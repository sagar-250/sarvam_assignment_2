"""Multi-user conversation simulation: tests BOTH halves of the system against
LLM-sourced raw material - the memory extractor (/observe, learning from a
conversation) and live memory-based correction (/run, applying what was
learned) - across many simulated users.

Design (see README's "Optional: LLM-assisted eval scale-out" section for the
full rationale): the LLM (tools/generate_entities.py) supplies diverse,
realistic mishearing/correction word pairs - that's the "benchmark material."
It is NOT trusted to decide what counts as correct system behavior. This
script builds each persona's "conversation" deterministically in Python
(carrier-sentence templates with the term substituted into the asr vs
corrected fields respectively - guaranteed correct by construction), feeds it
through the REAL /observe pipeline, reads the REAL resulting memory state back
from the system, and only THEN predicts what /run should do - by applying the
same documented rule used throughout eval/dataset.jsonl (active memory -> must
correct with its stored canonical form; inactive candidate -> must not correct;
no matching memory -> must never intervene on ordinary text). That rule is
applied by this script's author, not re-derived by calling decision.py, so the
check is not circular.

Deliberately mixes mention counts (1x / 2x / 3x) per persona so every run
exercises the low-confidence, just-activated, and reinforced-active paths
across many independently generated vocabularies - not just the hand-picked
names in eval/dataset.jsonl.

Usage:
    python eval/simulate_users.py

Requires eval/generated/entities_raw.jsonl to already exist (see
tools/generate_entities.py) - this script itself makes NO LLM calls and needs
no credentials, keeping it reproducible by anyone who clones the repo.
"""
import json
import os
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

EVAL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"
ENTITIES_PATH = EVAL_DIR / "generated" / "entities_raw.jsonl"
DB_PATH = str(RESULTS_DIR / "_simulation_run.db")

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

RNG_SEED = 20260904  # fixed seed -> byte-for-byte reproducible simulation
ENTITIES_PER_PERSONA = 3
MENTION_PLAN = [1, 2, 3]  # term[0] mentioned once, term[1] twice, term[2] three times

TEMPLATES = {
    "person_name": [
        "call {X} now",
        "remind me to email {X} tomorrow",
        "can you tell {X} about the meeting",
        "send the report to {X}",
        "ask {X} to join the call",
        "meet {X} at noon",
    ],
    "product_name": [
        "restart the {X} app",
        "check {X} settings",
        "the {X} service crashed again",
        "update {X} to the latest version",
        "install {X} on my laptop",
        "the {X} dashboard looks great",
    ],
    "place_name": [
        "flying to {X} tomorrow",
        "the office in {X} is closed",
        "meeting is scheduled in {X}",
        "we are relocating to {X}",
        "book a flight to {X}",
        "the conference is in {X} this year",
    ],
}

FILLER_UTTERANCES = [
    "what is the weather today",
    "set a timer for ten minutes",
    "play some music",
    "what time is it",
    "add milk to the shopping list",
    "turn off the lights",
    "how far is the nearest gas station",
    "read my latest email",
    "what is on my calendar today",
    "set an alarm for seven am",
    "how many days until the weekend",
    "what is the capital of France",
]


def load_entities() -> list[dict]:
    if not ENTITIES_PATH.exists():
        print(f"ERROR: {ENTITIES_PATH} not found. Run tools/generate_entities.py first.")
        sys.exit(1)
    return [json.loads(l) for l in ENTITIES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def build_personas(entities: list[dict], rng: random.Random) -> list[dict]:
    shuffled = entities[:]
    rng.shuffle(shuffled)
    personas = []
    for i in range(0, len(shuffled) - ENTITIES_PER_PERSONA + 1, ENTITIES_PER_PERSONA):
        group = shuffled[i : i + ENTITIES_PER_PERSONA]
        personas.append({"persona_id": f"user_{i // ENTITIES_PER_PERSONA + 1:03d}", "terms": group})
    return personas


def carrier(term: dict, template_idx: int, field: str) -> str:
    templates = TEMPLATES[term["kind"]]
    template = templates[template_idx % len(templates)]
    value = term["surface_asr"] if field == "asr" else term["surface_canonical"]
    return template.format(X=value)


def build_conversation(persona: dict, rng: random.Random) -> tuple[list[dict], dict]:
    """Returns (utterances, plan) where plan records, per term, which
    template indices were used for teaching (so the follow-up test can use a
    genuinely unseen template - testing recall, not repetition)."""
    utterances = []
    plan = {}
    for term, mention_count in zip(persona["terms"], MENTION_PLAN):
        used_templates = rng.sample(range(len(TEMPLATES[term["kind"]])), mention_count)
        for idx in used_templates:
            utterances.append(
                {
                    "asr": carrier(term, idx, "asr"),
                    "corrected": carrier(term, idx, "corrected"),
                    "term_surface_asr": term["surface_asr"],
                }
            )
        remaining_templates = [i for i in range(len(TEMPLATES[term["kind"]])) if i not in used_templates]
        follow_up_idx = rng.choice(remaining_templates) if remaining_templates else used_templates[0]
        plan[term["surface_asr"]] = {
            "term": term,
            "mention_count": mention_count,
            "follow_up_template_idx": follow_up_idx,
        }

    filler_sample = rng.sample(FILLER_UTTERANCES, min(5, len(FILLER_UTTERANCES)))
    for f in filler_sample:
        utterances.append({"asr": f, "corrected": f, "term_surface_asr": None})

    rng.shuffle(utterances)
    return utterances, plan


def reset() -> None:
    client.post("/api/reset").raise_for_status()


def observe(asr: str, corrected: str) -> dict:
    r = client.post("/api/observe", json={"asr": asr, "corrected": corrected})
    r.raise_for_status()
    return r.json()


def run(asr: str) -> dict:
    r = client.post("/api/run", json={"asr": asr})
    r.raise_for_status()
    return r.json()


def memories() -> list[dict]:
    return client.get("/api/memories").json()


def simulate_persona(persona: dict, rng: random.Random) -> dict:
    reset()
    utterances, plan = build_conversation(persona, rng)

    conversation_log = []
    latencies = []
    for u in utterances:
        t0 = time.perf_counter()
        result = observe(u["asr"], u["corrected"])
        latencies.append((time.perf_counter() - t0) * 1000)
        conversation_log.append(
            {"asr": u["asr"], "corrected": u["corrected"], "learned": result["learned"]}
        )

    final_memories = {m["observed_form"]: m for m in memories()}

    term_results = []
    anomalies = []
    for surface_asr, info in plan.items():
        term = info["term"]
        expected_evidence = info["mention_count"]
        mem = final_memories.get(surface_asr)

        actual_evidence = mem["evidence_count"] if mem else 0
        actual_active = mem["active"] if mem else False

        if actual_evidence != expected_evidence:
            anomalies.append(
                f"{surface_asr}: intended {expected_evidence} mentions, "
                f"memory shows evidence_count={actual_evidence} "
                f"(diff.py likely split phrasing into a different observed_form - inspect conversation_log)"
            )

        follow_up_asr = carrier(term, info["follow_up_template_idx"], "asr")
        t0 = time.perf_counter()
        run_result = run(follow_up_asr)
        latencies.append((time.perf_counter() - t0) * 1000)

        applied = {iv["observed_form"]: iv for iv in run_result["interventions"]}
        skipped = {ni["observed_form"]: ni for ni in run_result["non_interventions"]}

        if actual_active:
            if surface_asr in applied and applied[surface_asr]["applied"] == term["surface_canonical"]:
                classification = "TP_useful_intervention"
            elif surface_asr in applied:
                classification = "FP_incorrect_intervention"
            else:
                classification = "FN_missed_intervention"
        else:
            if surface_asr in skipped or surface_asr not in applied:
                classification = "TN"
            else:
                classification = "FP_unnecessary_intervention"

        term_results.append(
            {
                "surface_asr": surface_asr,
                "surface_canonical": term["surface_canonical"],
                "kind": term["kind"],
                "intended_mentions": expected_evidence,
                "actual_evidence_count": actual_evidence,
                "actual_active": actual_active,
                "follow_up_asr": follow_up_asr,
                "follow_up_formatted": run_result["formatted"],
                "follow_up_memory_aware": run_result["memory_aware"],
                "classification": classification,
            }
        )

    filler_check = []
    filler_candidates = [u for u in utterances if u["term_surface_asr"] is None]
    for u in rng.sample(filler_candidates, min(2, len(filler_candidates))):
        result = run(u["asr"])
        false_positive = len(result["interventions"]) > 0
        if false_positive:
            anomalies.append(f"FALSE POSITIVE on filler utterance: '{u['asr']}' -> {result['interventions']}")
        filler_check.append({"asr": u["asr"], "false_positive": false_positive})

    return {
        "persona_id": persona["persona_id"],
        "terms": [t for t in persona["terms"]],
        "conversation_log": conversation_log,
        "final_memory_state": list(final_memories.values()),
        "term_results": term_results,
        "filler_check": filler_check,
        "anomalies": anomalies,
        "latencies_ms": latencies,
    }


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    entities = load_entities()
    rng = random.Random(RNG_SEED)
    personas = build_personas(entities, rng)

    print(f"Simulating {len(personas)} personas from {len(entities)} LLM-generated entities...")

    persona_results = []
    for persona in personas:
        persona_results.append(simulate_persona(persona, rng))

    reset()

    all_classifications = [tr["classification"] for pr in persona_results for tr in pr["term_results"]]
    counts = {}
    for c in all_classifications:
        counts[c] = counts.get(c, 0) + 1

    all_latencies = [lat for pr in persona_results for lat in pr["latencies_ms"]]
    all_anomalies = [(pr["persona_id"], a) for pr in persona_results for a in pr["anomalies"]]

    tp = counts.get("TP_useful_intervention", 0)
    fp = counts.get("FP_unnecessary_intervention", 0) + counts.get("FP_incorrect_intervention", 0)
    fn = counts.get("FN_missed_intervention", 0)
    tn = counts.get("TN", 0)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    summary = {
        "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "personas": len(personas),
        "entities_used": len(personas) * ENTITIES_PER_PERSONA,
        "term_checks": len(all_classifications),
        "counts": counts,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "false_positives_on_filler": sum(1 for pr in persona_results for fc in pr["filler_check"] if fc["false_positive"]),
        "anomaly_count": len(all_anomalies),
        "latency_p50_ms": round(statistics.median(all_latencies), 3) if all_latencies else 0.0,
        "latency_p95_ms": round(sorted(all_latencies)[int(0.95 * (len(all_latencies) - 1))], 3) if all_latencies else 0.0,
    }

    output = {"summary": summary, "anomalies": all_anomalies, "personas": persona_results}
    (RESULTS_DIR / "simulation_results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    (RESULTS_DIR / "simulation_report.md").write_text(render_report(output), encoding="utf-8")

    print(f"\n{len(personas)} personas, {summary['term_checks']} term checks:")
    print(f"  precision={summary['precision']} recall={summary['recall']}")
    print(f"  counts={counts}")
    print(f"  false positives on filler text: {summary['false_positives_on_filler']}")
    print(f"  anomalies (mention-count mismatches etc.): {summary['anomaly_count']}")
    print(f"  latency p50={summary['latency_p50_ms']}ms p95={summary['latency_p95_ms']}ms")
    print("\nResults written to eval/results/simulation_results.json and simulation_report.md")

    return 0 if fp == 0 and summary["false_positives_on_filler"] == 0 else 1


def render_report(output: dict) -> str:
    s = output["summary"]
    lines = [
        "# Kivi Memory System - Multi-User Simulation Report",
        "",
        f"Run at: {s['run_at']}",
        "",
        "LLM-sourced raw material (tools/generate_entities.py), deterministically assembled into "
        "per-persona conversations, run through the real /observe and /run pipeline, graded against "
        "the documented activation rule (not against the LLM's opinion). See eval/simulate_users.py "
        "docstring for the full methodology.",
        "",
        f"**{s['personas']} simulated users, {s['entities_used']} LLM-generated personal terms, "
        f"{s['term_checks']} recall checks.**",
        "",
        "## Summary",
        "",
        f"- Precision: {s['precision']}, Recall: {s['recall']}",
        f"- Counts: {s['counts']}",
        f"- False positives on ordinary filler text (should always be 0): {s['false_positives_on_filler']}",
        f"- Anomalies (mention-count mismatches - see below): {s['anomaly_count']}",
        f"- Latency: p50={s['latency_p50_ms']}ms, p95={s['latency_p95_ms']}ms",
        "",
    ]

    if output["anomalies"]:
        lines.append("## Anomalies")
        lines.append("")
        for persona_id, a in output["anomalies"]:
            lines.append(f"- **{persona_id}**: {a}")
        lines.append("")

    lines.append("## Per-Persona Detail")
    lines.append("")
    for pr in output["personas"]:
        lines.append(f"### {pr['persona_id']}")
        lines.append("")
        lines.append("Terms taught this session:")
        for tr in pr["term_results"]:
            lines.append(
                f"- `{tr['surface_asr']}` -> `{tr['surface_canonical']}` ({tr['kind']}), "
                f"intended {tr['intended_mentions']}x, actual evidence_count={tr['actual_evidence_count']}, "
                f"active={tr['actual_active']}"
            )
        lines.append("")
        lines.append("Conversation fed through /observe:")
        for turn in pr["conversation_log"]:
            learned_str = ", ".join(f"{l['observed_form']}->{l['canonical_form']} ({l['status']})" for l in turn["learned"]) or "(nothing new)"
            lines.append(f"- ASR: \"{turn['asr']}\" / Corrected: \"{turn['corrected']}\" -> learned: {learned_str}")
        lines.append("")
        lines.append("Follow-up recall test (unseen sentence per term):")
        for tr in pr["term_results"]:
            lines.append(
                f"- \"{tr['follow_up_asr']}\" -> \"{tr['follow_up_memory_aware']}\" "
                f"[{tr['classification']}]"
            )
        lines.append("")
        if pr["filler_check"]:
            fp_flags = [fc["asr"] for fc in pr["filler_check"] if fc["false_positive"]]
            lines.append(
                f"Filler false-positive check: {len(pr['filler_check'])} ordinary sentences tested, "
                f"{len(fp_flags)} false positive(s)."
            )
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
