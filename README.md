# Kivi — Phonetic Word Memory

![tests](https://img.shields.io/badge/tests-62%2F62%20passing-brightgreen)
![eval](https://img.shields.io/badge/eval-26%2F26%20passing-brightgreen)
![precision/recall/F1](https://img.shields.io/badge/P%2FR%2FF1-1.0-brightgreen)
![python](https://img.shields.io/badge/python-3.11%2B-blue)

A word-level memory system for Kivi's dictation pipeline. It learns personal terms (names, products, places) from the corrections a user makes, and reuses that memory later — but only once a correction is genuinely confirmed, never off a single guess.

Built for Sarvam's **"The Words Kivi Keeps"** take-home (Backend-Focused Full Stack).

## How it works

| Stage | Example |
|---|---|
| **1. ASR output** — raw speech-to-text | `ask aditya to review the sarvam kiwi service` |
| **2. Formatted output** — sentence-cased, punctuated (deterministic, no NER/LLM) | `Ask aditya to review the sarvam kiwi service.` |
| **3. Memory-aware output** — personal terms corrected | `Ask Aaditya to review the sarvam Kivi service.` |

At request time: `tokenize()` → `retrieve()` → `decide()` → `apply()`. Every decision — applied or deliberately left alone — comes back with a human-readable `reason` and `explanation`.

## Quick start

Full setup, the primary review path, and every interaction to try are in **[RUN.md](RUN.md)**. Short version:

```bash
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
python scripts/init_db.py && python scripts/seed.py
uvicorn backend.app:app --port 8000
```

Open `http://localhost:8000`. No environment variables or credentials required for the primary path.

## Features

- **Two-confirmation memory** — one correction creates a `candidate`; a second, independent, agreeing one activates it. `confidence = min(1.0, evidence_count / 3)`, applied only once `evidence_count ≥ 2` **and** `confidence ≥ 0.6` (the two thresholds cross at exactly the same point, so they can never disagree).
- **Deterministic correction path** — no LLM anywhere between formatting and applying a correction, so evaluation is fully reproducible with byte-exact expected strings.
- **Explains every decision** — `POST /run` returns `interventions[]` and `non_interventions[]`, each with a reason: already correct, below confidence, ambiguous without context, or conflicting evidence.
- **Ambiguous-word gating** — "apple" (the fruit) needs a nearby supporting cue ("stock", "Inc") before the brand meaning applies; "kiwi" isn't over-gated just because it's also an ordinary word.
- **Fuzzy + exact + multi-word matching** — bounded edit-distance tolerance for ASR typos, exact multi-word spans ("yolk sity" → "York City"), possessives, ALL-CAPS, punctuation-adjacent tokens.
- **Bulk teaching, two ways** — a list of `(asr, corrected)` pairs, *or* raw already-correct conversation text with no ASR side at all, via a free offline NER pass with optional LLM refinement.
- **Optional LLM-assisted grouping** — merges adjacent word-level corrections into one multi-word entity when appropriate; off by default, never makes results worse when unavailable.
- **Fully inspectable** — every memory's complete evidence history and every decision's reasoning is queryable, not just current state.

## Architecture

```
Browser (frontend/, vanilla JS)  ->  FastAPI (backend/app.py, routes.py)
  +-- POST /observe(/bulk)            -> diff.py -> memory_service.py -> SQLite
  +-- POST /learn-from-conversations  -> ner_extraction.py + entity_extraction.py (LLM, optional)
  +-- POST /run                       -> formatter -> tokenizer -> retrieval -> decision -> apply
  +-- GET/DELETE /memories, POST /reset
```

| Module | Responsibility |
|---|---|
| `backend/formatter.py` | Deterministic ASR → formatted text (sentence case + punctuation only) |
| `backend/diff.py` | Diffs formatted baseline vs. correction into `(observed_form, canonical_form, ...)` pairs |
| `backend/memory_service.py` | Learn / list / delete / reset lifecycle |
| `backend/tokenizer.py` | Lossless tokenization — offsets, casing, possessive suffixes preserved |
| `backend/retrieval.py` | Exact + bounded fuzzy candidate matching, longest-span-first |
| `backend/decision.py` | The rules deciding intervene vs. leave-alone, each with a reason |
| `backend/apply.py` | Substitutes only decided spans back into the original string |
| `backend/ner_extraction.py` | Free, offline spaCy NER for bulk conversation import |
| `backend/entity_extraction.py` | Optional LLM entity extraction — refines NER, never required |
| `backend/grouping.py` | Optional LLM-assisted merging of adjacent corrections |

**Database** — two tables, mirrored in `scripts/schema.sql`: `memory` (one row per learned `(observed_form, canonical_form)` pair, `UNIQUE` constraint lets competing corrections coexist as separate candidates) and `evidence` (append-only log, `source_type` = `observed_pair` or `conversation_extraction`). `scripts/init_db.py` is the idempotent "migration" — no Alembic, one schema version for this scope.

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/observe` | Teach one `(asr, corrected)` pair |
| `POST /api/observe/bulk` | Teach many pairs at once, deterministic |
| `POST /api/learn-from-conversations` | Teach from correct-text-only transcripts (NER + optional LLM) |
| `POST /api/run` | Run a transcript through formatting + memory correction |
| `GET /api/memories` / `DELETE /api/memories/{id}` | Inspect / forget a memory |
| `GET /api/memories/{id}` | Full evidence history for one memory |
| `POST /api/reset` | Clear all memory and evidence |

## Testing & evaluation

```bash
python -m pytest tests/ -q        # 62 unit/integration tests
python eval/run_eval.py           # 26 hand-authored cases
```

26 cases (`eval/dataset.jsonl`, 16 categories) cover confirmation thresholds, already-correct guards, ambiguous-word gating (both directions), fuzzy typos (accept + reject), multi-word entities, possessives, punctuation edge cases, and conflicting evidence — well beyond the brief's single worked example. Each case preserves its inputs, expected/actual output, the full memory-state snapshot, and per-span decision reasons. Every intervention is classified `TP_useful` / `FP_unnecessary` / `FP_unexpected` / `FN_missed` / `TN`, so useful corrections are reported separately from incorrect ones. Committed baseline: **26/26 passing, precision/recall/F1 = 1.0, p95 latency ~5-10ms, zero LLM calls or cost** (`eval/results/report.md`).

<details>
<summary>Capability → eval-case traceability (click to expand)</summary>

<br>

| Capability | Case(s) |
|---|---|
| Needs 2 confirmations before acting | `low_confidence_single_obs_005` vs `activation_after_second_obs_006` |
| Leaves text alone if already correct | `product_already_correct_004` |
| Ignores terms never seen | `unseen_term_007/008` |
| Blocks ambiguous common word without supporting context | `ambiguous_common_word_negative_009` (fruit "apple") |
| ...but allows it with supporting context | `ambiguous_common_word_positive_010` ("Apple" + "stock", "company") |
| Doesn't over-gate ordinary words off the curated list | `ambiguous_word_not_overgated_011` ("kiwi") |
| Handles ALL-CAPS and mixed-case ASR | `case_variation_all_caps_012`, `case_variation_mixed_013` |
| Handles possessive forms ("aditya's") | `possessive_after_activation_014` |
| Handles tokens adjacent to punctuation | `punctuation_adjacent_*_015/016/017` |
| Handles multi-word entities ("yolk sity" → "York City") | `multiword_entity_018` |
| Resolves conflicting evidence toward the more recent | `conflicting_evidence_020` |
| Fuzzy-matches small ASR typos within a budget | `fuzzy_typo_accept_021` |
| ...but never matches unrelated/very short words | `fuzzy_typo_reject_far_022`, `fuzzy_reject_short_word_023` |
| Applies multiple independent memories in one sentence | `multiple_active_memories_one_sentence_026` |
</details>

<details>
<summary><b>Optional: LLM-assisted eval scale-out</b> — 99 entities, 33 simulated users, click to expand</summary>

<br>

On top of the 26 hand-reasoned cases, `tools/generate_entities.py` + `eval/simulate_users.py` stress the memory extractor and live correction at bigger scale with independent vocabulary. The LLM is never the judge of correctness — it only brainstorms realistic mishearing pairs (`"chenai" -> "Chennai"`, `"googel pixel" -> "Google Pixel"`, `"krystopher" -> "Christopher"`; 99 total, committed to `eval/generated/entities_raw.jsonl`). This whole section is optional appendix material — `RUN.md`'s primary review path doesn't touch it and needs no credentials.

**Provider history, told straight:**
1. Asking the LLM to generate full ASR/corrected conversation turns directly failed outright on the first model tried — it echoed few-shot examples instead of writing new ones. Sentence construction moved out of the LLM entirely; only the raw mishearing→canonical pairs are LLM-sourced.
2. NVIDIA NIM was tried first. Only `nvidia/nemotron-3-ultra-550b-a55b` (of 5 spot-checked) worked reliably, and even that endpoint was degraded under load — most calls timed out.
3. Switched to Mistral (`open-mistral-nemo`): ~4s/batch, no retries needed, 188 req/min vs. NVIDIA's flaky 40. Now the default (`KIVI_LLM_PROVIDER=nvidia` to switch back). Trade-off: needed more manual cleanup — ~20 of ~120 raw pairs dropped by hand for being backwards (`"mumbai" -> "Mumbay"`) or nonsensical (`"delhi" -> "Delhi Metro"`, a different entity, not a mishearing).

**`eval/simulate_users.py`**: groups the 99 entities into 33 personas (3 terms each), builds a ~10-turn conversation per persona deterministically (fixed carrier-sentence templates, correct by construction, terms mentioned 1x/2x/3x on purpose to exercise every confidence stage), feeds it through the real `POST /api/observe`, reads back real memory state via `GET /api/memories`, tests recall with a held-out follow-up sentence per term via `POST /api/run`, and grades against the same rule used everywhere else in this README. Run: `python tools/generate_entities.py` (needs `MISTRAL_KEY`) then `python eval/simulate_users.py` (needs nothing — pure Python, fixed seed, fully reproducible). Results: `eval/results/simulation_report.md` / `simulation_results.json`.

**What it found — two real bugs, both fixed:**
1. **Digits silently dropped.** `KingSeW3` got mangled by the tokenizer's old letters-only regex. Neither the 26 hand cases nor unit tests covered this (no hand-picked name had a digit). Fixed by allowing digits after a word's first letter.
2. **A whole observation could silently vanish.** `diff.py`'s insert-merge logic pulled the *entire* preceding matched run into a multi-word insert, not just the adjacent word — so `"meeting is scheduled in nassau"` + inserted `"county"` produced one 5-word span that `MAX_SPAN_TOKENS` rejected outright, with no error and no memory row. Caught via `evidence_count=0` showing up where it shouldn't. Fixed to only pull in the one word next to the insertion point.

Committed run: 99 entities, 33 personas, 99 recall checks → precision and recall both **1.0**, zero false positives on filler text. 18 flagged "anomalies" all trace to one understood, correct pattern: when only part of a phrase is a genuine misspelling (`san fransisco → San Francisco`), the system learns the narrower, more useful sub-span (`fransisco → Francisco`) rather than the whole phrase — the simulation's own bookkeeping flags that as a mismatch even though the behavior is right.
</details>

## Bulk-teaching from existing corrected data

The "Bulk Teach" UI section (and its two endpoints) supports whichever form historical data happens to be in:

**Mode 1 — corrected pairs** (`POST /api/observe/bulk`, always available, no credentials). A list of `(asr, corrected)` pairs, taught via the same `learn()` path as `POST /observe`, just looped. Each pair validated independently — one malformed pair reports its own `error` without aborting the batch.

**Mode 2 — corrected text only, no ASR side** (`POST /api/learn-from-conversations`). There's nothing to diff, so extraction — not diffing — finds the personal terms, via two merged passes: **spaCy NER** (`backend/ner_extraction.py`, free, offline, always attempted, no API key) and an **optional LLM refinement** (`backend/entity_extraction.py`, attempted only if credentials are configured; a missing key is normal, not an error). Results are merged by normalized form — the LLM's classification wins on overlap, and the response's `sources: ["ner"|"llm"|"ner","llm"]` field shows which pass found each entity.

<details>
<summary>Implementation details, verified findings, and a real bug caught in testing</summary>

<br>

**NER's recall gap, verified not assumed** (`tests/test_ner_extraction.py`): `en_core_web_sm` reliably tags places/orgs ("Mumbai" → GPE, "Google" → ORG) and catches a name with strong verb context ("Sarah called" → PERSON), but recall drops sharply without that context and to zero on names it has little training signal for — "Rahul" is missed entirely in "Meet Rahul tomorrow...", the same sentence shape that also misses "John". Live-verified on `"Meet Aaditya tomorrow to discuss the Kivi launch in Bengaluru with Sarvam."`: `sources=["ner","llm"]` for "Kivi"/"Bengaluru" (both agreed), `sources=["llm"]` for "Aaditya"/"Sarvam" (NER's gap, LLM caught it). This is the payoff of the hybrid: with only the NER model installed (one-time, credential-free download), Mode 2 already works with zero LLM credentials — an LLM key only improves coverage, never required for it to function.

The LLM pass verifies every returned span is an actual verbatim substring of the input (never trusting an invented name). Entities are deduplicated *within* each conversation before upserting — one document mentioning a name five times contributes one evidence increment, not five, so a single document can't fake independent multi-source confirmation. `Evidence.source_type = "conversation_extraction"` keeps this provenance inspectable per-row.

**A real bug caught during testing, not a hypothetical:** Mode 1's per-pair response snapshots `evidence_count`/`confidence`/`active` immediately after each `learn()` call rather than deferring to the end of the loop. SQLAlchemy's identity map means if pair 2 in a batch reinforces the same `Memory` row pair 1 just created, both results reference the *same* mutable ORM object — reading it lazily afterward would make pair 1's reported state silently reflect pair 2's later mutation. Caught by a test asserting pair 1 stays `new_candidate`/inactive while pair 2 shows `activated` in the same batch.
</details>

## Optional: LLM-assisted grouping for adjacent corrections

Mitigates a fragmentation limitation (below): teaching `"new yolk sity" -> "New York City"` learns `"new" -> "New"` and `"yolk sity" -> "York City"` as two separate memories, since word-level diffing can't tell "these are one entity" from "these are unrelated." With `KIVI_LLM_GROUPING_ENABLED=true` and credentials, one LLM call per adjacent pair asks exactly that: "new" + "yolk sity" → merges; "sarvam" + "kiwi" (the brief's own flagship example) → correctly stays separate, despite being textually adjacent too.

<details>
<summary>Design constraints and verification</summary>

<br>

- **Off by default; every failure mode degrades to existing behavior, never worse.** Flag off, missing credentials, malformed output, or network error all fall back to the original unmerged pairs (`backend/grouping.py::maybe_group_adjacent_pairs`).
- **Only textually-adjacent corrections are ever offered to the LLM** — checked via a plain substring test first.
- **Shared by both bulk-teach and single-teach** (`memory_service.py::learn()`, used by both `/observe` and `/observe/bulk`).
- Verified against both the merge case and the no-merge case with mocked responses (`tests/test_grouping.py`) plus a real end-to-end check. Not part of the primary credential-free eval/test run.
</details>

## Design decisions

<details>
<summary>Formatter scope, determinism, schema, re-casing rules — click to expand</summary>

<br>

**The formatter is deliberately minimal** — sentence-initial capitalization and terminal punctuation, nothing else. The brief's own cover example shows a formatted stage that already capitalizes a name it's never seen (`aditya → Aditya`); reproducing that faithfully needs real NER/LLM judgment, explicitly out of scope for phonetic memory. The formatter stays honestly dumb; memory supplies personal correctness. Stated scope boundary, not a gap.

**Memory application is deterministic substitution, not an LLM prompt-injection step.** "Placing the memory into the formatting prompt" is a legitimate real-product approach, but Part Two needs a reproducible, byte-exact evaluation — a generative step there would make it non-deterministic. Determinism won.

**No Alembic.** One schema version for this scope; an idempotent `CREATE TABLE IF NOT EXISTS` plus committed `scripts/schema.sql` covers it.

**No mandatory LLM key.** The reviewing agent "will not infer missing setup... or contact you for clarification," so the primary path needs zero credentials. `backend/llm_formatter.py` is a documented, unimplemented, off-by-default extension point.

**Single user, no auth.** Out of scope per the brief's own "smallest system" framing.

**Diffing merges a trailing insert into the preceding token**, so expansions like `apple → Apple Inc` (not a same-length replacement) still get learned as one pair instead of silently dropped.

**Sentence-initial re-casing never gets learned; mid-sentence re-casing does.** The formatter already capitalizes the first word of every sentence, so a correction that's only that ("ask" → "Ask") would just re-teach it its own job. A mid-sentence, casing-only correction ("sohail" → "Sohail") is different — the formatter deliberately never guesses a lowercase mid-sentence word is a proper noun, so that gap is memory's to fill, learned like any other term. A recasing token bordering a multi-word replace (teaching "new yolk sity" → "New York City" also teaches "new" → "New" separately) becomes its own independent entry rather than folding into the neighbor — the diff can't tell that apart from an unrelated recasing next to an unrelated replacement ("sarvam" next to "kiwi" → "Kivi", which must stay separate). Applying both substitutions together still reconstructs the phrase correctly; see Limitations for the one case where this can look inconsistent.
</details>

## Limitations (known and deliberate)

- **Multi-word spans match exactly** — no fuzzy tolerance for spans > 1 token.
- **A taught multi-word entity can fragment** into separate single/multi-word memories by default (see "Design decisions" above) — **mitigated, off by default**, by the LLM-assisted grouping pass.
- **Ambiguous-word stoplist is small and hand-curated**, not a full dictionary — deliberately, to avoid over-gating ordinary product names that are also real words ("kiwi").
- **No automatic decay** for superseded memories; conflicting evidence competes at retrieval time instead. Manual `DELETE /api/memories/{id}` is the "forget" control.
- **Entity-type inference in the core diff path is a coarse heuristic** (nearby cue words), not real NER — real NER only enters via the optional bulk-conversation path.
- **Single-user, SQLite only** — multi-tenant use would need a `user_id` column and a server-grade database.
- **The tokenizer only treats letters/digits as part of a "word."** A period inside a canonical form (`Finn.no`) tokenizes as two words and loses the period on substitution — found during testing, not assumed. Digits mid-word (`Web3`) work fine.

## AI use

Built with [Claude Code](https://claude.com/claude-code) (Anthropic). An initial research report explored the design space; a plan built from that report plus a direct read of the assignment PDF is what this repository implements — several original choices got revised during implementation (the diff/formatter split, the insert-merge fix, localized entity-type inference, the deterministic-vs-LLM trade-off) based on hand-verifying actual behavior against the brief's example and the eval cases, not writing code first and cherry-picking what passed. All code, tests, the eval dataset, and this README were written and checked iteratively in-session. Every number cited above was actually executed and checked, not asserted from memory.
