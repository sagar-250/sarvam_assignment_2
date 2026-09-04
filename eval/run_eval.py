"""Reproducible evaluation harness for the Kivi phonetic memory system.

Usage:
    python eval/run_eval.py

Writes eval/results/results.json (machine-readable) and
eval/results/report.md (human-readable) and exits non-zero if any case
fails its classification (see `classify()` below).

Each case is run against a freshly reset database (POST /reset before every
case) so cases never leak state into one another - this is what makes the
run reproducible regardless of dataset ordering. The harness talks to the
app in-process via FastAPI's TestClient (no separate server process needed),
calling the exact same routes the interactive demo uses.
"""
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

EVAL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"
DATASET_PATH = EVAL_DIR / "dataset.jsonl"
DB_PATH = str(RESULTS_DIR / "_eval_run.db")

os.environ["KIVI_DB_PATH"] = DB_PATH

from sqlalchemy.orm import sessionmaker

import backend.db as db_module
from backend.db import get_engine
from backend.models import Base

_engine = get_engine(DB_PATH)
Base.metadata.create_all(_engine)
db_module.SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)

from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def load_dataset() -> list[dict]:
    cases = []
    with open(DATASET_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def reset() -> None:
    r = client.post("/api/reset")
    r.raise_for_status()


def observe(asr: str, corrected: str) -> dict:
    r = client.post("/api/observe", json={"asr": asr, "corrected": corrected})
    r.raise_for_status()
    return r.json()


def run(asr: str) -> dict:
    r = client.post("/api/run", json={"asr": asr})
    r.raise_for_status()
    return r.json()


def memories_snapshot() -> list[dict]:
    r = client.get("/api/memories")
    r.raise_for_status()
    return r.json()


def classify_case(case: dict, response: dict) -> dict:
    """Per-span TP/FP/FN/TN classification against the case's expectations,
    plus overall pass/fail for the case as a whole."""
    actual_intervened = {iv["observed_form"] for iv in response["interventions"]}
    actual_no_intervene = {ni["observed_form"] for ni in response["non_interventions"]}

    expected_intervene = set(case["expected_intervention_spans"])
    expected_no_intervene = set(case["expected_no_intervention_spans"])

    span_results = []
    for span in expected_intervene:
        if span in actual_intervened:
            span_results.append((span, "TP_useful_intervention"))
        elif span in actual_no_intervene:
            span_results.append((span, "FN_missed_intervention"))
        else:
            span_results.append((span, "FN_missed_intervention_no_candidate"))
    for span in expected_no_intervene:
        if span in actual_no_intervene:
            span_results.append((span, "TN"))
        elif span in actual_intervened:
            span_results.append((span, "FP_unnecessary_intervention"))
        else:
            span_results.append((span, "TN_no_candidate"))
    # anything the system intervened on that we did NOT expect at all
    for span in actual_intervened - expected_intervene - expected_no_intervene:
        span_results.append((span, "FP_unexpected_intervention"))

    formatted_correct = response["formatted"] == case["expected_formatted"]
    output_correct = response["memory_aware"] == case["expected_memory_aware"]
    spans_ok = all(
        cls.startswith("TP") or cls.startswith("TN") for _, cls in span_results
    )
    passed = formatted_correct and output_correct and spans_ok

    return {
        "span_results": span_results,
        "formatted_correct": formatted_correct,
        "output_correct": output_correct,
        "passed": passed,
    }


def run_db_growth_check() -> dict:
    reset()
    checkpoints = []
    seed_path = EVAL_DIR.parent / "data" / "seed_observations.jsonl"
    observations = [json.loads(l) for l in seed_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    dataset_observations = []
    for case in load_dataset():
        dataset_observations.extend(case["observations"])
    all_obs = (observations * 4) + dataset_observations  # pad out for a clearer growth curve

    fed = 0
    checkpoint_targets = {10, 25, 50, len(all_obs)}
    for obs in all_obs:
        observe(obs["asr"], obs["corrected"])
        fed += 1
        if fed in checkpoint_targets:
            r = client.get("/api/memories")
            mem_count = len(r.json())
            checkpoints.append({"observations_fed": fed, "memory_rows": mem_count})
    reset()
    return {"checkpoints": checkpoints}


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_dataset()

    results = []
    latencies = []
    counts = {
        "TP_useful_intervention": 0,
        "FP_unnecessary_intervention": 0,
        "FP_unexpected_intervention": 0,
        "FN_missed_intervention": 0,
        "FN_missed_intervention_no_candidate": 0,
        "TN": 0,
        "TN_no_candidate": 0,
    }
    by_category: dict[str, dict] = {}

    for case in cases:
        reset()
        for obs in case["observations"]:
            observe(obs["asr"], obs["corrected"])

        t0 = time.perf_counter()
        response = run(case["asr"])
        latency_ms = (time.perf_counter() - t0) * 1000
        latencies.append(latency_ms)

        snapshot = memories_snapshot()
        classification = classify_case(case, response)

        cat = case["category"]
        cat_entry = by_category.setdefault(
            cat, {"cases_total": 0, "cases_passed": 0, **{k: 0 for k in counts}}
        )
        cat_entry["cases_total"] += 1
        cat_entry["cases_passed"] += 1 if classification["passed"] else 0

        for _, cls in classification["span_results"]:
            counts[cls] = counts.get(cls, 0) + 1
            cat_entry[cls] = cat_entry.get(cls, 0) + 1

        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "notes": case["notes"],
                "inputs": {"observations": case["observations"], "asr": case["asr"]},
                "expected": {
                    "formatted": case["expected_formatted"],
                    "memory_aware": case["expected_memory_aware"],
                    "intervention_spans": case["expected_intervention_spans"],
                    "no_intervention_spans": case["expected_no_intervention_spans"],
                },
                "actual": {
                    "formatted": response["formatted"],
                    "memory_aware": response["memory_aware"],
                    "interventions": response["interventions"],
                    "non_interventions": response["non_interventions"],
                },
                "memory_state": snapshot,
                "classification": classification,
                "latency_ms": round(latency_ms, 3),
                "passed": classification["passed"],
            }
        )

    reset()

    def prf(c: dict) -> dict:
        tp = c.get("TP_useful_intervention", 0)
        fp = c.get("FP_unnecessary_intervention", 0) + c.get("FP_unexpected_intervention", 0)
        fn = c.get("FN_missed_intervention", 0) + c.get("FN_missed_intervention_no_candidate", 0)
        precision = tp / (tp + fp) if (tp + fp) else 1.0
        recall = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}

    overall_prf = prf(counts)
    category_summary = {cat: {**prf(c), "counts": c} for cat, c in by_category.items()}

    latencies_sorted = sorted(latencies)
    p50 = statistics.median(latencies_sorted) if latencies_sorted else 0.0
    p95 = (
        latencies_sorted[int(0.95 * (len(latencies_sorted) - 1))] if latencies_sorted else 0.0
    )
    sla_ms = 50.0

    db_growth = run_db_growth_check()

    total_cases = len(cases)
    failed_cases = [r for r in results if not r["passed"]]

    summary = {
        "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_cases": total_cases,
        "passed_cases": total_cases - len(failed_cases),
        "failed_cases": len(failed_cases),
        "overall": overall_prf,
        "counts": counts,
        "by_category": category_summary,
    }

    output = {
        "summary": summary,
        "latency": {
            "p50_ms": round(p50, 3),
            "p95_ms": round(p95, 3),
            "max_ms": round(max(latencies), 3) if latencies else 0.0,
            "sla_ms": sla_ms,
            "sla_met": p95 < sla_ms,
        },
        "db_growth": db_growth,
        "model_usage": {
            "llm_enabled": False,
            "llm_calls": 0,
            "estimated_cost_usd": 0.0,
            "note": "N/A - the default formatter is rule-based; no LLM calls occur in this configuration.",
        },
        "cases": results,
    }

    (RESULTS_DIR / "results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    (RESULTS_DIR / "report.md").write_text(render_report(output), encoding="utf-8")

    print(f"Ran {total_cases} cases: {summary['passed_cases']} passed, {summary['failed_cases']} failed.")
    print(f"Overall precision={overall_prf['precision']} recall={overall_prf['recall']} f1={overall_prf['f1']}")
    print(f"Latency p50={output['latency']['p50_ms']}ms p95={output['latency']['p95_ms']}ms")
    print("Results written to eval/results/results.json and eval/results/report.md")

    return 0 if not failed_cases else 1


def render_report(output: dict) -> str:
    s = output["summary"]
    lines = []
    lines.append("# Kivi Memory System - Evaluation Report")
    lines.append("")
    lines.append(f"Run at: {s['run_at']}")
    lines.append("")
    lines.append(f"**{s['passed_cases']} / {s['total_cases']} cases passed.**")
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- Precision: {s['overall']['precision']}")
    lines.append(f"- Recall: {s['overall']['recall']}")
    lines.append(f"- F1: {s['overall']['f1']}")
    lines.append("")
    lines.append(
        f"- Useful interventions (TP): {s['counts'].get('TP_useful_intervention', 0)}"
    )
    lines.append(
        f"- Unnecessary/incorrect interventions (FP): "
        f"{s['counts'].get('FP_unnecessary_intervention', 0) + s['counts'].get('FP_unexpected_intervention', 0)}"
    )
    lines.append(
        f"- Missed interventions (FN): "
        f"{s['counts'].get('FN_missed_intervention', 0) + s['counts'].get('FN_missed_intervention_no_candidate', 0)}"
    )
    lines.append(
        f"- Correct non-interventions (TN): "
        f"{s['counts'].get('TN', 0) + s['counts'].get('TN_no_candidate', 0)}"
    )
    lines.append("")
    lines.append("## By Category")
    lines.append("")
    lines.append("| Category | Cases | Precision | Recall | F1 | TP | FP | FN | TN |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for cat, c in sorted(output["summary"]["by_category"].items()):
        cc = c["counts"]
        fp = cc.get("FP_unnecessary_intervention", 0) + cc.get("FP_unexpected_intervention", 0)
        fn = cc.get("FN_missed_intervention", 0) + cc.get("FN_missed_intervention_no_candidate", 0)
        tn = cc.get("TN", 0) + cc.get("TN_no_candidate", 0)
        cases_str = f"{cc.get('cases_passed', 0)}/{cc.get('cases_total', 0)}"
        lines.append(
            f"| {cat} | {cases_str} | {c['precision']} | {c['recall']} | {c['f1']} | "
            f"{cc.get('TP_useful_intervention', 0)} | {fp} | {fn} | {tn} |"
        )
    lines.append("")
    lines.append("## Latency")
    lines.append("")
    lat = output["latency"]
    lines.append(f"- p50: {lat['p50_ms']}ms, p95: {lat['p95_ms']}ms, max: {lat['max_ms']}ms")
    lines.append(f"- SLA: p95 < {lat['sla_ms']}ms -> {'MET' if lat['sla_met'] else 'NOT MET'}")
    lines.append("")
    lines.append("## Database Growth")
    lines.append("")
    lines.append("| Observations fed | Memory rows |")
    lines.append("|---|---|")
    for cp in output["db_growth"]["checkpoints"]:
        lines.append(f"| {cp['observations_fed']} | {cp['memory_rows']} |")
    lines.append("")
    lines.append("## Model Usage / Cost")
    lines.append("")
    lines.append(f"- {output['model_usage']['note']}")
    lines.append("")

    failed = [c for c in output["cases"] if not c["passed"]]
    lines.append(f"## Failures ({len(failed)})")
    lines.append("")
    if not failed:
        lines.append("None.")
    for c in failed:
        lines.append(f"### {c['id']} ({c['category']})")
        lines.append("")
        lines.append(f"- Notes: {c['notes']}")
        lines.append(f"- Inputs: `{json.dumps(c['inputs'])}`")
        lines.append(f"- Expected formatted: `{c['expected']['formatted']}`")
        lines.append(f"- Actual formatted:   `{c['actual']['formatted']}`")
        lines.append(f"- Expected memory-aware: `{c['expected']['memory_aware']}`")
        lines.append(f"- Actual memory-aware:   `{c['actual']['memory_aware']}`")
        lines.append(f"- Memory state at run time: `{json.dumps(c['memory_state'])}`")
        lines.append(f"- Span classification: `{c['classification']['span_results']}`")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
