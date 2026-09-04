"""Generates a pool of diverse (surface_asr -> surface_canonical) personal-word
pairs via the NVIDIA LLM, for use by eval/simulate_users.py.

The LLM is used ONLY for what it's actually good at here: producing varied,
realistic mishearing/name pairs. It is NOT trusted to decide what the correct
system behavior is - that's still reasoned mechanically downstream (see
eval/simulate_users.py's docstring). This script also does NOT build full
conversations with the LLM (tested and found unreliable - a small model
(meta/llama-3.2-11b-vision-instruct) just echoed few-shot examples instead of
keeping "asr" vs "corrected" fields distinct; the larger reasoning model used
by default here, nvidia/nemotron-3-ultra-550b-a55b, is far more reliable for
this narrower term-generation task, but full free-form conversation
generation was never revisited since the deterministic-template approach
below is also more robust and requires no further LLM trust). Full carrier
sentences are instead built deterministically in Python.

Usage:
    python tools/generate_entities.py [--target 60]

Writes eval/generated/entities_raw.jsonl. Safe to re-run - accumulates until
--target valid entities are reached, skipping duplicates already on disk.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.llm_client import chat_json

OUT_PATH = Path(__file__).resolve().parent.parent / "eval" / "generated" / "entities_raw.jsonl"

SYSTEM_PROMPT = "You output strict JSON only. No markdown, no commentary, no code fences."

BATCH_SIZE = 8

USER_PROMPT_TEMPLATE = """A speech-to-text system mishears personal words. Examples of the pattern \
(mishearing -> correct spelling): "aditya" -> "Aaditya", "kiwi" -> "Kivi", "jon" -> "John", \
"sara" -> "Sarah", "catlin" -> "Kaitlyn".

Generate {n} NEW examples of this pattern as a JSON array, covering a mix of Indian and Western \
first names, tech product names, and city/place names. Do not reuse: {avoid}.

Each item: {{"surface_asr": "lowercase phonetic mishearing, one or two words", \
"surface_canonical": "Correct Spelling", "kind": "person_name" or "product_name" or "place_name"}}. \
Most should be a single word; up to 3 of the 15 may be two-word phrases (e.g. a full name or a \
two-word place/product). surface_asr and surface_canonical must always be genuinely different \
spellings (never identical, never just a casing difference - reject pairs like "sam"/"Sam"). \
Output ONLY the JSON array."""

MAX_SPAN_WORDS = 3  # matches backend.config.MAX_SPAN_TOKENS


def _valid(item: dict) -> bool:
    asr = item.get("surface_asr", "").strip()
    can = item.get("surface_canonical", "").strip()
    kind = item.get("kind", "")
    if not asr or not can:
        return False
    if len(asr.split()) > MAX_SPAN_WORDS or len(can.split()) > MAX_SPAN_WORDS:
        return False
    if asr.lower() == can.lower():  # identical or casing-only - not memory-worthy, see backend/diff.py
        return False
    if kind not in ("person_name", "product_name", "place_name"):
        return False
    return True


def load_existing() -> list[dict]:
    if not OUT_PATH.exists():
        return []
    return [json.loads(l) for l in OUT_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def _save(entities: list[dict]) -> None:
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for e in entities:
            f.write(json.dumps(e) + "\n")


def generate(target: int) -> list[dict]:
    entities = load_existing()
    seen = {e["surface_asr"].lower() for e in entities}

    attempts = 0
    while len(entities) < target and attempts < 20:
        attempts += 1
        avoid = ", ".join(sorted(seen)[-20:]) or "none yet"
        prompt = USER_PROMPT_TEMPLATE.format(n=BATCH_SIZE, avoid=avoid)
        print(f"[generate_entities] batch {attempts}: requesting {BATCH_SIZE}, have {len(entities)}/{target}...", flush=True)
        try:
            batch = chat_json(SYSTEM_PROMPT, prompt, temperature=1.0, max_tokens=2000)
        except Exception as e:  # noqa: BLE001
            print(f"  batch failed: {e}", flush=True)
            continue

        if not isinstance(batch, list):
            print("  unexpected response shape, skipping batch", flush=True)
            continue

        added = 0
        for item in batch:
            if not isinstance(item, dict) or not _valid(item):
                continue
            key = item["surface_asr"].lower()
            if key in seen:
                continue
            seen.add(key)
            entities.append(
                {
                    "surface_asr": item["surface_asr"].strip().lower(),
                    "surface_canonical": item["surface_canonical"].strip(),
                    "kind": item["kind"],
                }
            )
            added += 1
        print(f"  +{added} valid ({len(batch) - added} rejected/duplicate)", flush=True)
        _save(entities)  # persist after every batch, so progress survives an interrupted run

    return entities


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=60)
    args = parser.parse_args()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entities = generate(args.target)
    _save(entities)

    by_kind: dict[str, int] = {}
    for e in entities:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    print(f"\nWrote {len(entities)} entities to {OUT_PATH}")
    print(f"By kind: {by_kind}")


if __name__ == "__main__":
    main()
