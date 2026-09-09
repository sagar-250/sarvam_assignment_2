"""Retrieval performance benchmark.

Measures backend.retrieval.retrieve() - which routes to one of two matching
strategies depending on memory-table size (config.RETRIEVAL_SMALL_TABLE_
THRESHOLD) - at increasing table sizes, and compares it against
`_legacy_retrieve()` below: a faithful reimplementation of the original,
pre-optimization algorithm (always a full-table load, then a linear
Levenshtein scan against every single-token row for every query token),
i.e. what you'd get *without* the router.

Usage:
    python eval/benchmark_retrieval.py

Writes eval/results/retrieval_benchmark.json (raw numbers) and
eval/results/retrieval_benchmark.md (human-readable report).

Runs entirely in-process against throwaway in-memory SQLite databases - one
fresh engine per table size, so backend.retrieval's per-engine SymSpell
cache is guaranteed to start cold for the "cold build" measurement at each
size, exactly like a freshly started server would see for its first request.
"""
import json
import random
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rapidfuzz.distance import Levenshtein
from sqlalchemy.orm import sessionmaker

from backend import config, retrieval
from backend.config import MAX_SPAN_TOKENS
from backend.db import get_engine
from backend.models import Base, Memory
from backend.retrieval import Candidate, _fuzzy_budget
from backend.tokenizer import tokenize, span_norm

EVAL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"

SIZES = [100, 1_000, 5_000, 20_000, 50_000]
REPEATS = 3  # timed repeats per measurement, averaged
FIXED_POOL_SIZE = 20  # words guaranteed present at every table size, for apples-to-apples queries

_CONSONANTS = "bcdfghjklmnpqrstvwxyz"
_VOWELS = "aeiou"


def _random_word(rng: random.Random, min_len: int = 4, max_len: int = 9) -> str:
    """A pronounceable-ish fake word (consonant/vowel alternating) so lengths
    and edit-distance behavior resemble the names/products this app deals with."""
    length = rng.randint(min_len, max_len)
    start_with_consonant = rng.random() < 0.7
    chars = []
    for i in range(length):
        if (i % 2 == 0) == start_with_consonant:
            chars.append(rng.choice(_CONSONANTS))
        else:
            chars.append(rng.choice(_VOWELS))
    return "".join(chars)


def _typo(word: str, rng: random.Random) -> str:
    """A single-edit-distance mutation of `word` (substitute one character)."""
    idx = rng.randrange(len(word))
    other = rng.choice([c for c in _VOWELS + _CONSONANTS if c != word[idx]])
    return word[:idx] + other + word[idx + 1 :]


# ---------------------------------------------------------------------------
# Legacy algorithm (pre-optimization, no router) - reproduced here since it
# no longer exists in backend/retrieval.py. This is the "what if every
# request always did a full-table load + brute-force scan" baseline.
# ---------------------------------------------------------------------------


def _legacy_load(session) -> dict[int, list[Memory]]:
    all_memories = session.query(Memory).all()
    by_token_count: dict[int, list[Memory]] = {}
    for m in all_memories:
        by_token_count.setdefault(m.token_count, []).append(m)
    return by_token_count


def _legacy_fuzzy_scan(norm: str, budget: int, single_token_rows: list[Memory]):
    best_distance = None
    fuzzy_rows: list[Memory] = []
    for row in single_token_rows:
        dist = Levenshtein.distance(norm, row.observed_form)
        if 0 < dist <= budget:
            if best_distance is None or dist < best_distance:
                best_distance = dist
                fuzzy_rows = [row]
            elif dist == best_distance:
                fuzzy_rows.append(row)
    return fuzzy_rows, best_distance


def _legacy_retrieve(session, tokens, by_token_count: dict[int, list[Memory]] | None = None) -> list[Candidate]:
    if not tokens:
        return []
    if by_token_count is None:
        by_token_count = _legacy_load(session)

    n = len(tokens)
    claimed: set[int] = set()
    candidates: list[Candidate] = []

    for start in range(n):
        if start in claimed:
            continue
        max_len = min(MAX_SPAN_TOKENS, n - start)
        matched_here = False
        for span_len in range(max_len, 0, -1):
            if any((start + k) in claimed for k in range(span_len)):
                continue
            window = tokens[start : start + span_len]
            norm = span_norm(window)

            exact_rows = [m for m in by_token_count.get(span_len, []) if m.observed_form == norm]
            if exact_rows:
                for row in exact_rows:
                    candidates.append(Candidate(start, start + span_len, row, "exact", 0))
                claimed.update(range(start, start + span_len))
                matched_here = True
                break

            if span_len == 1:
                budget = _fuzzy_budget(len(norm))
                if budget > 0:
                    fuzzy_rows, best_distance = _legacy_fuzzy_scan(norm, budget, by_token_count.get(1, []))
                    if fuzzy_rows:
                        for row in fuzzy_rows:
                            candidates.append(Candidate(start, start + 1, row, "fuzzy", best_distance))
                        claimed.add(start)
                        matched_here = True
                        break
        if not matched_here:
            continue
    return candidates


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------


@dataclass
class Timed:
    mean_ms: float
    median_ms: float
    p95_ms: float
    max_ms: float

    @staticmethod
    def from_samples(samples_s: list[float]) -> "Timed":
        ms = sorted(s * 1000 for s in samples_s)
        p95_idx = int(0.95 * (len(ms) - 1)) if len(ms) > 1 else 0
        return Timed(
            mean_ms=round(statistics.mean(ms), 4),
            median_ms=round(statistics.median(ms), 4),
            p95_ms=round(ms[p95_idx], 4),
            max_ms=round(max(ms), 4),
        )

    def to_dict(self) -> dict:
        return {"mean_ms": self.mean_ms, "median_ms": self.median_ms, "p95_ms": self.p95_ms, "max_ms": self.max_ms}


def _time_repeated(fn, repeats: int = REPEATS) -> Timed:
    samples = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return Timed.from_samples(samples)


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


def build_session(size: int, rng: random.Random, fixed_pool: list[str]):
    engine = get_engine(":memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    seen = set(fixed_pool)
    rows = [
        Memory(observed_form=w, canonical_form=w.capitalize(), entity_type="other", token_count=1,
               evidence_count=2, confidence=1.0, active=True)
        for w in fixed_pool
    ]
    while len(rows) < size:
        w = _random_word(rng)
        if w in seen:
            continue
        seen.add(w)
        rows.append(
            Memory(observed_form=w, canonical_form=w.capitalize(), entity_type="other", token_count=1,
                   evidence_count=2, confidence=1.0, active=True)
        )
    session.bulk_save_objects(rows)
    session.commit()
    return session


def run_for_size(size: int, rng: random.Random) -> dict:
    fixed_pool = [_random_word(rng) for _ in range(FIXED_POOL_SIZE)]
    fixed_pool = [w if len(w) > 4 else w + "xo" for w in fixed_pool]  # guarantee nonzero fuzzy budget

    exact_queries = fixed_pool[:10]
    typo_queries = [_typo(w, rng) for w in fixed_pool[10:16]]
    miss_queries = ["banana", "umbrella", "keyboard", "mountain", "sandwich", "octopus"]

    transcripts = [
        f"please contact {exact_queries[0]} and {typo_queries[0]} about the {miss_queries[0]} today",
        f"{typo_queries[1]} confirmed the {exact_queries[1]} update for {miss_queries[1]}",
        f"can you ask {typo_queries[2]} to review the {exact_queries[2]} {miss_queries[2]} again",
        f"{exact_queries[3]} and {typo_queries[3]} spoke about the {miss_queries[3]} yesterday",
        f"remind {typo_queries[4]} that {exact_queries[4]} needs the {miss_queries[4]} by tomorrow",
    ]
    tokenized_transcripts = [tokenize(t) for t in transcripts]

    path = "small" if size <= config.RETRIEVAL_SMALL_TABLE_THRESHOLD else "large"

    # --- new implementation: retrieve() itself (router included) ---
    session = build_session(size, rng, fixed_pool)
    retrieval.retrieve(session, tokenized_transcripts[0])  # warm up caches once, like a live server would
    full_retrieve = _time_repeated(lambda: [retrieval.retrieve(session, toks) for toks in tokenized_transcripts])

    if path == "large":
        # fresh, untouched engine so the very first call is a guaranteed cache miss
        cold_session = build_session(size, rng, fixed_pool)
        cold_build = _time_repeated(lambda: retrieval._get_symspell(cold_session), repeats=1)
        symspell = retrieval._get_symspell(session)  # warm, from the already-touched session
        fuzzy_step = _time_repeated(lambda: [symspell.lookup(w, _fuzzy_budget(len(w))) for w in typo_queries])
        exact_step = _time_repeated(
            lambda: retrieval._batched_exact_lookup(session, retrieval._collect_spans(tokenized_transcripts[0]))
        )
        cold_session.close()
    else:
        all_memories = session.query(Memory).all()
        single_token_rows = [m for m in all_memories if m.token_count == 1]
        by_key: dict[tuple[int, str], list[Memory]] = {}
        for m in all_memories:
            by_key.setdefault((m.token_count, m.observed_form), []).append(m)
        cold_build = None  # no index built on this path
        fuzzy_step = _time_repeated(
            lambda: [_legacy_fuzzy_scan(w, _fuzzy_budget(len(w)), single_token_rows) for w in typo_queries]
        )
        exact_step = _time_repeated(lambda: [by_key.get((1, w), []) for w in exact_queries])

    session.close()

    # --- legacy (pre-optimization, no router) baseline ---
    legacy_session = build_session(size, rng, fixed_pool)
    legacy_table_load = _time_repeated(lambda: legacy_session.query(Memory).all())
    by_token_count = _legacy_load(legacy_session)  # for the isolated fuzzy-step measurement only
    legacy_single_token_rows = by_token_count.get(1, [])
    legacy_fuzzy_scan = _time_repeated(
        lambda: [_legacy_fuzzy_scan(w, _fuzzy_budget(len(w)), legacy_single_token_rows) for w in typo_queries]
    )
    # No pre-loaded by_token_count here - each call reloads the table, matching
    # what retrieve() does per call (i.e. real per-request cost, not batch-
    # amortized cost across the 5 transcripts).
    legacy_full_retrieve = _time_repeated(
        lambda: [_legacy_retrieve(legacy_session, toks) for toks in tokenized_transcripts]
    )
    legacy_session.close()

    return {
        "memory_rows": size,
        "path_used": path,
        "new": {
            "cold_symspell_build": cold_build.to_dict() if cold_build else None,
            "exact_step": exact_step.to_dict(),
            "fuzzy_step_per_batch_of_6": fuzzy_step.to_dict(),
            "full_retrieve_per_transcript_batch_of_5": full_retrieve.to_dict(),
        },
        "legacy": {
            "full_table_load": legacy_table_load.to_dict(),
            "fuzzy_scan_per_batch_of_6": legacy_fuzzy_scan.to_dict(),
            "full_retrieve_per_transcript_batch_of_5": legacy_full_retrieve.to_dict(),
        },
        "speedup": {
            "fuzzy_step_x": round(legacy_fuzzy_scan.mean_ms / fuzzy_step.mean_ms, 1) if fuzzy_step.mean_ms else None,
            "full_retrieve_x": round(legacy_full_retrieve.mean_ms / full_retrieve.mean_ms, 1) if full_retrieve.mean_ms else None,
        },
    }


def render_report(results: list[dict]) -> str:
    lines = []
    lines.append("# Retrieval Performance Benchmark")
    lines.append("")
    lines.append(
        "Compares backend.retrieval.retrieve() (routes to an in-memory strategy below "
        f"{config.RETRIEVAL_SMALL_TABLE_THRESHOLD:,} memory rows, and an indexed+SymSpell "
        "strategy above it) against a reimplementation of the original algorithm with no "
        "router - always a full-table load, then a Levenshtein scan against every "
        "single-token row per query token."
    )
    lines.append("")
    lines.append(f"All times are per-batch (see column headers), averaged over {REPEATS} repeats, "
                  "on a freshly built in-memory SQLite DB per size.")
    lines.append("")
    lines.append("## retrieve() vs. no-router legacy baseline")
    lines.append("")
    lines.append("| Memory rows | Path used | New full retrieve /5 transcripts (ms) | "
                  "Legacy full retrieve /5 transcripts (ms) | Speedup |")
    lines.append("|---|---|---|---|---|")
    for r in results:
        n = r["new"]["full_retrieve_per_transcript_batch_of_5"]["mean_ms"]
        lg = r["legacy"]["full_retrieve_per_transcript_batch_of_5"]["mean_ms"]
        lines.append(f"| {r['memory_rows']:,} | {r['path_used']} | {n} | {lg} | {r['speedup']['full_retrieve_x']}x |")
    lines.append("")
    lines.append("## Step-by-step (new implementation)")
    lines.append("")
    lines.append("| Memory rows | Path | Cold SymSpell build (ms) | Exact-match step (ms) | Fuzzy-match step /6 (ms) |")
    lines.append("|---|---|---|---|---|")
    for r in results:
        n = r["new"]
        cold = n["cold_symspell_build"]["mean_ms"] if n["cold_symspell_build"] else "n/a (small-table path)"
        lines.append(f"| {r['memory_rows']:,} | {r['path_used']} | {cold} | {n['exact_step']['mean_ms']} | {n['fuzzy_step_per_batch_of_6']['mean_ms']} |")
    lines.append("")
    lines.append("## Legacy (no-router) baseline")
    lines.append("")
    lines.append("| Memory rows | Full-table load (ms) | Fuzzy scan /6 (ms) | Full retrieve /5 transcripts (ms) |")
    lines.append("|---|---|---|---|")
    for r in results:
        lg = r["legacy"]
        lines.append(
            f"| {r['memory_rows']:,} | {lg['full_table_load']['mean_ms']} | "
            f"{lg['fuzzy_scan_per_batch_of_6']['mean_ms']} | "
            f"{lg['full_retrieve_per_transcript_batch_of_5']['mean_ms']} |"
        )
    lines.append("")
    lines.append(
        "Note: \"cold SymSpell build\" only happens once per DB engine per change to the "
        "single-token dictionary (see backend/retrieval.py's fingerprint cache), and only "
        "on the large-table path - it is not paid on every request, and not paid at all "
        "below the router threshold."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)

    results = []
    for size in SIZES:
        print(f"Benchmarking at {size:,} memory rows...")
        results.append(run_for_size(size, rng))

    output = {
        "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repeats": REPEATS,
        "small_table_threshold": config.RETRIEVAL_SMALL_TABLE_THRESHOLD,
        "sizes": results,
    }
    (RESULTS_DIR / "retrieval_benchmark.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    (RESULTS_DIR / "retrieval_benchmark.md").write_text(render_report(results), encoding="utf-8")

    print("")
    for r in results:
        sp = r["speedup"]
        print(
            f"{r['memory_rows']:>7,} rows ({r['path_used']:>5}): full_retrieve new="
            f"{r['new']['full_retrieve_per_transcript_batch_of_5']['mean_ms']}ms  "
            f"legacy={r['legacy']['full_retrieve_per_transcript_batch_of_5']['mean_ms']}ms  "
            f"speedup={sp['full_retrieve_x']}x"
        )
    print("")
    print("Results written to eval/results/retrieval_benchmark.json and eval/results/retrieval_benchmark.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
