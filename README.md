# Kivi: Phonetic Word Memory

This is a small word-level memory system for Kivi's dictation pipeline. It learns personal terms (names, products, places) from the corrections a user makes, and later uses that memory to fix the same terms when they show up again. It never guesses at something it hasn't actually confirmed.

Built for Sarvam's "The Words Kivi Keeps" take-home (Backend-Focused Full Stack).

## The three transcript stages

1. **ASR output**: raw speech-to-text, like `ask aditya to review the sarvam kiwi service`
2. **Formatted output**: sentence-cased and punctuated, like `Ask aditya to review the sarvam kiwi service.`
3. **Memory-aware output**: personal terms corrected, like `Ask Aaditya to review the sarvam Kivi service.`

Run `python eval/run_eval.py`, or use the UI, to watch this whole journey happen end to end. Setup is in `RUN.md`.

## What "remembering a word" actually means here

A memory entry maps an **observed form** (what ASR tends to produce, normalized) to a **canonical form** (what the user actually wants to see), and it carries a confidence score built from repeated evidence:

- One correction creates a **candidate**. It's not trusted yet, because it could just be a one-off typo.
- A **second, independent, agreeing correction** activates it. Confidence works out to `min(1.0, evidence_count / 3)`, and the memory only gets applied once `evidence_count >= 2` AND `confidence >= 0.6`. With the default thresholds, both conditions cross at the exact same point, so they can never disagree with each other.
- Every observation gets logged, whether it was actually learned or not, in an append-only `evidence` table. So you can trace any memory's full history, not just look at its current state.
- Deleting a memory manually is just `DELETE /api/memories/{id}` (there's a button for it in the UI's memory table too). That's the "forget this" control.

This was a deliberate call: one correction isn't enough to change what the system outputs. Requiring a second confirmation is what stops a single ASR fluke, or a user typo, from quietly corrupting every transcript after it.

## What it can tell apart (beyond the one example in the brief)

The brief gives a single worked example (`aditya → Aaditya`, `kiwi → Kivi`) and asks for more. Here's what this system additionally handles, each one backed by a real case in `eval/dataset.jsonl`:

| Capability | Example |
|---|---|
| Needs 2 confirmations before it acts | `low_confidence_single_obs_005` vs `activation_after_second_obs_006` |
| Leaves text alone if it's already correct | `product_already_correct_004` |
| Ignores terms it's never seen | `unseen_term_007/008` |
| Blocks an ambiguous common word if there's no supporting context | `ambiguous_common_word_negative_009` (fruit "apple") |
| ...but allows it once there's supporting context | `ambiguous_common_word_positive_010` ("Apple" plus "stock", "company") |
| Doesn't over-gate ordinary words that aren't on the curated ambiguity list | `ambiguous_word_not_overgated_011` ("kiwi" is a real word too, but it isn't gated) |
| Handles ALL-CAPS and mixed-case ASR fine | `case_variation_all_caps_012`, `case_variation_mixed_013` |
| Handles possessive forms ("aditya's") | `possessive_after_activation_014` |
| Handles tokens sitting next to punctuation (commas, parens, periods) | `punctuation_adjacent_*_015/016/017` |
| Handles multi-word entities ("yolk sity" → "York City") | `multiword_entity_018` |
| Resolves conflicting evidence toward the more recently reinforced correction | `conflicting_evidence_020` |
| Fuzzy-matches small ASR typos within an edit-distance budget | `fuzzy_typo_accept_021` |
| ...but never fuzzy-matches unrelated or very short words (negative controls) | `fuzzy_typo_reject_far_022`, `fuzzy_reject_short_word_023` |
| Applies multiple independent memories correctly in one sentence | `multiple_active_memories_one_sentence_026` |

And it explains every decision, not just the ones it acted on. `POST /api/run` returns `interventions[]` for what got applied and `non_interventions[]` for what matched a memory but got deliberately left alone, with a reason attached. More on that in "Retrieval & decision logic" below.

## Architecture

```
Browser (frontend/index.html, vanilla JS)
        |  fetch()
        v
FastAPI app (backend/app.py, backend/routes.py)
        |
        +-- POST /api/observe --> backend/diff.py --> backend/memory_service.py --> SQLite
        |
        +-- POST /api/run     --> backend/formatter.py --> backend/tokenizer.py
        |                          --> backend/retrieval.py --> backend/decision.py
        |                          --> backend/apply.py --> memory-aware text
        |
        +-- GET/DELETE /api/memories, POST /api/reset --> backend/memory_service.py
```

- **`backend/formatter.py`**: turns ASR into formatted text. Deterministic and rule-based, more on why below.
- **`backend/diff.py`**: diffs the *formatted* baseline against the user's correction, so it can isolate the personal-term corrections from ordinary formatting noise. Produces `(observed_form, canonical_form, token_count, entity_type)` pairs.
- **`backend/memory_service.py`**: handles the learn/list/delete/reset lifecycle described above.
- **`backend/tokenizer.py`**: tokenizes words while keeping exact character offsets, casing, and possessive suffixes, so any substitution later can be lossless.
- **`backend/retrieval.py`**: finds candidate memory matches in a transcript. Exact match first, then a bounded edit-distance fuzzy match for single tokens. Multi-word spans get matched greedily, longest first, without overlapping.
- **`backend/decision.py`**: the five rules that decide whether a retrieved candidate actually gets applied (see below), each one paired with a human-readable `reason` and `explanation`.
- **`backend/apply.py`**: substitutes only the decided spans back into the original string, keeping every untouched bit of whitespace and punctuation exactly as it was.

### Database schema

Two tables (`backend/models.py`, mirrored in `scripts/schema.sql`):

- **`memory`**: one row per learned `(observed_form, canonical_form)` pair, with `entity_type`, `token_count`, `evidence_count`, `confidence`, `active`, and timestamps. There's a `UNIQUE(observed_form, canonical_form)` constraint, which is what lets two competing corrections for the same observed form live side by side as separate candidate rows instead of one silently overwriting the other. See "conflicting evidence" below.
- **`evidence`**: an append-only log of every observation, linked back to whichever memory row it affected. This is what makes a memory's whole history inspectable, not just its current state.

`python scripts/init_db.py` creates both tables idempotently, and that's the project's "migration." A full migration framework like Alembic would be overkill here, since the schema only has one version for this assignment's scope. `scripts/schema.sql` is committed as a human-readable DDL mirror.

## Retrieval and decision logic

For every span in a new transcript that matches any memory, active or not, one of these rules decides what happens:

1. **Already-correct guard**: if the span already reads as the canonical form, it's left alone with `reason=already_correct`.
2. **Confidence gate**: the matched memory has to be `active` (2+ confirmations, confidence at or above 0.6). If not, it's left alone with `reason=below_confidence_threshold`, and the explanation quotes the actual evidence count and confidence.
3. **Ambiguous-common-word context gate**: a small, hand-curated set of words that are also ordinary dictionary words (right now, just `"apple"`, in `backend/decision.py`'s `COMMON_WORD_CUES`) need a nearby supporting cue word before the specialized meaning gets applied. This is deliberately not a full dictionary, see Limitations for why.
4. **Conflicting candidates**: if multiple active memories match the same span with different canonical forms, the highest-confidence one wins, tie-broken by whichever was reinforced more recently, and the explanation says so.
5. This one's a mechanic rather than a gate: possessive suffixes get stripped before matching and reattached after substitution, and the memory's own stored casing is what actually shows up in the output, not a re-casing of whatever the ASR happened to produce. That's why ALL-CAPS ASR still resolves correctly.

All of this happens deterministically. No LLM call is anywhere in this path, and the next section explains why.

## Design decisions and tradeoffs

**The formatter is deliberately minimal**, doing sentence-initial capitalization and terminal punctuation and nothing else. The brief's own cover example shows a formatted stage that already capitalizes a name it's never seen before (`aditya → Aditya`). Reproducing that faithfully would need real NER or LLM judgment, and that's explicitly out of scope here, this assignment is about phonetic memory, not general formatting. Rather than fake that with brittle heuristics, the formatter stays honestly dumb, and memory is what supplies the personal correctness. That's actually the core idea being tested, not a shortcut around it. It's a stated scope boundary, not a gap I'm hoping nobody notices.

**Memory application is deterministic substitution, not an LLM prompt-injection step.** You could imagine "placing the relevant memory into the formatting prompt" as a legitimate approach in a real product. But Part Two of this assignment needs a reproducible evaluation with byte-exact expected strings, and a generative step in that path would make the evaluation non-deterministic and much harder to actually verify, which runs against "your evaluation must be reproducible... we should be able to verify the conclusions you present." So determinism won out over that flexibility.

**No Alembic.** The schema has exactly one version for what this assignment needs. `scripts/init_db.py` (an idempotent `CREATE TABLE IF NOT EXISTS`) plus a committed `scripts/schema.sql` covers "database schema and migrations" without pulling in a migration framework that has nothing to migrate.

**No mandatory LLM key.** The brief says the reviewing agent "will not infer missing setup... or contact you for clarification," so the primary review path needs zero credentials to run. `backend/llm_formatter.py` exists as a documented, off-by-default extension point (`KIVI_USE_LLM_FORMATTER`, `KIVI_LLM_API_KEY`), but it's not implemented and never required.

**Single user, no auth.** That's out of scope per the brief's closing line: "build the smallest one that makes Kivi feel as though it has met this person before." Not a multi-tenant system.

**Diffing merges a trailing insert into the preceding token** (`backend/diff.py`), so expansions like `apple → Apple Inc`, which aren't a same-length replacement, still get learned as one pair instead of getting silently dropped by `difflib`'s default replace-only handling.

**Sentence-initial re-casing never gets learned, but mid-sentence re-casing does.** The formatter already capitalizes the first word of every sentence, so a correction that's only that (e.g. "ask" → "Ask") would just re-teach the formatter its own job and gets skipped. A mid-sentence, casing-only correction (e.g. "sohail" → "Sohail") is different: the formatter deliberately never guesses that a lowercase mid-sentence word is a proper noun (see `backend/formatter.py`), so that gap is exactly what the memory layer exists to fill, and it's learned like any other personal term. A recasing token that borders a multi-word replace (e.g. teaching "new yolk sity" → "New York City" also teaches "new" → "New" as its own single-word memory, separate from "yolk sity" → "York City") is learned as its own independent entry rather than folded into the neighboring entity - the diff has no way to tell that case apart from an unrelated recasing next to an unrelated replacement (e.g. "sarvam" next to "kiwi" → "Kivi" in the brief's own flagship example, which must stay separate). Applying both substitutions together still reconstructs the full phrase correctly; see "Limitations" below for the one case where this can look inconsistent.

## Bulk-teaching from existing corrected data

The "Bulk Teach" section in the UI (and its two API endpoints) supports whichever form a reviewer's historical data happens to be in:

**Mode 1 - corrected pairs** (`POST /api/observe/bulk`, always available, no credentials). Accepts a list of `(asr, corrected)` pairs and teaches all of them in one request - the same `learn()` path `POST /observe` already uses, just looped. Deterministic, no LLM, no schema change. Each pair is validated and processed independently (`backend/memory_service.py::learn_bulk_pairs`), so one malformed pair reports its own `error` in the response instead of aborting the rest of the batch.

One implementation detail worth calling out because it was a real bug caught during testing, not a hypothetical: the per-pair response snapshots `evidence_count`/`confidence`/`active` immediately after each `learn()` call rather than deferring to the end of the loop. SQLAlchemy's identity map means if pair 2 in a batch reinforces the same `Memory` row pair 1 just created, both `LearnResult`s end up referencing the *same* mutable ORM object - reading it lazily after the whole loop finishes would make pair 1's reported state silently reflect pair 2's later mutation instead of its own. Caught by a test asserting pair 1 status is `new_candidate`/inactive and pair 2 is `activated` in the same batch.

**Mode 2 - corrected text only, no ASR side** (`POST /api/learn-from-conversations`). For historical data that's just finished, already-correct conversation transcripts with no paired "what ASR originally heard" - there's nothing to diff, so entity *extraction*, not diffing, has to find the personal terms. Two passes feed the same `_upsert_memory()` every other learning path uses:

1. **`backend/ner_extraction.py`** - spaCy NER (`en_core_web_sm`), free, fully offline, always attempted, no API key needed. Real but genuinely imperfect, verified directly rather than assumed (`tests/test_ner_extraction.py`): it reliably tags places and orgs ("Mumbai" -> GPE, "Google" -> ORG) and catches a name with strong verb context ("Sarah called" -> PERSON), but recall drops sharply without that context and to zero on names the model has little training signal for - "Rahul" is missed entirely in "Meet Rahul tomorrow...", the exact sentence shape that also misses "John". Invented product names fare no better.
2. **`backend/entity_extraction.py`** - the LLM pass described below, now a *refinement* rather than a requirement: attempted only if credentials are configured, and a missing key is treated as "this pass didn't run," never an error - the whole endpoint must never be worse than NER alone just because no key is set. Any other failure (malformed output, network error after internal retries) is swallowed the same way, so a transient LLM hiccup can't discard entities NER already found.

Results are merged by normalized form; when both passes find the same entity, the LLM's classification wins (more context to work with) and the response's `sources: ["ner"] | ["llm"] | ["ner","llm"]` field records which pass(es) actually found it - live-verified end-to-end on `"Meet Aaditya tomorrow to discuss the Kivi launch in Bengaluru with Sarvam."`: `sources=["ner","llm"]` for "Kivi"/"Bengaluru" (both passes agreed), `sources=["llm"]` for "Aaditya"/"Sarvam" (NER's real recall gap, LLM caught what NER missed). **This is the practical payoff of the hybrid design**: with the NER model installed (a one-time, credential-free download - see RUN.md), Mode 2 now works in the primary review path with zero LLM credentials; if credentials happen to be configured too, coverage only improves, never regresses.

The LLM extraction itself: `backend/entity_extraction.py` asks the LLM to spot personal entities directly (people, products, places), verifies every returned span is an actual verbatim substring of the input (never trusting the model to have invented a name that isn't really there). Entities are deduplicated *within* each conversation before upserting either way, so one document mentioning a name five times contributes one evidence increment, not five - a single document can't fake independent multi-source confirmation. `Evidence.source_type = "conversation_extraction"` (vs. `"observed_pair"` for everything else) keeps this provenance inspectable per-row. Verified with mocked responses in `tests/test_memory_service.py`/`tests/test_entity_extraction.py`/`tests/test_ner_extraction.py`/`tests/test_api.py` (including the "nothing available" and "credentials missing but NER still works" cases specifically), and confirmed live end-to-end (real Mistral call plus real spaCy inference, correct merge/dedupe/activation, and the resulting memories actually applying on `/run`) during manual testing.

## Optional: LLM-assisted grouping for adjacent corrections

The fragmentation limitation just described (`"new yolk sity" -> "New York City"` splitting into two memories) has an optional, off-by-default mitigation: `backend/grouping.py`. When two learned corrections are written directly adjacent to each other in the corrected text, and `KIVI_LLM_GROUPING_ENABLED=true` plus real provider credentials (`MISTRAL_KEY`/`NVIDIA_KEY`) are set, one LLM call is made per adjacent pair asking a single yes/no question: is this one multi-word entity, or two unrelated corrections that just happen to sit next to each other? "new" + "yolk sity" → merges into one `"new yolk sity" -> "New York City"` memory. "sarvam" + "kiwi" in the brief's own flagship example → stays two separate memories, because they're unrelated brand names, not one entity, even though they're textually adjacent too.

This is deliberately narrow and safe by construction, not a general NER pass:
- **Off by default, and every failure mode degrades to the existing deterministic behavior**, never to a worse one: flag off, missing credentials, a malformed LLM response, or any network error all fall back to returning the original unmerged pairs unchanged (`backend/grouping.py::maybe_group_adjacent_pairs`). The LLM is only ever asked to adjudicate a candidate the deterministic diff already found - it can't invent a merge the diff didn't already produce the pieces for.
- **Only textually-adjacent corrections are ever offered to the LLM** (checked via a plain substring test before any call is made), so it can't be asked about spans that aren't actually next to each other in the source text.
- **Wired into both bulk-teach and single-teach** (`backend/memory_service.py::learn()`, called by both `POST /observe` and `POST /observe/bulk`), so it benefits either path without duplicated logic.
- Verified against both the "should merge" case (`new` + `yolk sity`) and the "should NOT merge" case (`sarvam` + `kiwi`, the assignment's own worked example) with mocked LLM responses in `tests/test_grouping.py`, plus an end-to-end check through the real `learn()` pipeline. Not part of the primary eval/tests run, which stay entirely credential-free.

## Limitations (known and deliberate)

- **Multi-word spans only match exactly.** There's no fuzzy tolerance for `token_count > 1` entries (see `multiword_requires_exact_match_019`). Fuzzy multi-word matching would be a fairly easy extension, it just wasn't needed to demonstrate the capability here.
- **A multi-word proper noun taught alongside a spelling fix can split into separate single-word and multi-word memories, by default.** Teaching `"new yolk sity" -> "New York City"` learns `"yolk sity" -> "York City"` (genuine spelling fix) and `"new" -> "New"` (mid-sentence recasing) as two independent entries, since the deterministic diff has no real entity extraction to tell "these two words are one name" from "these two words are unrelated" (see `multiword_entity_018`, `multiword_requires_exact_match_019`, and README "Diffing merges..." above). Applying both together still reconstructs the phrase correctly when the whole thing was mistyped, but it can also produce a partially-corrected, inconsistent-looking result when only part of the phrase is mistyped (e.g. `"new york city"` typed correctly except for casing becomes `"New york city"` - `"new"` matches its own memory, `"york city"` doesn't match `"yolk sity"` exactly, so it's left alone). **Mitigated, off by default:** see "Optional: LLM-assisted grouping for adjacent corrections" above - `KIVI_LLM_GROUPING_ENABLED=true` with credentials asks the LLM to decide, per adjacent pair, whether it's genuinely one entity, without affecting the primary credential-free path.
- **The ambiguous-word stoplist is small and hand-curated**, not a full dictionary (see `ambiguous_word_not_overgated_011`). A full dictionary would gate too aggressively and block ordinary product names that happen to also be real words, like "kiwi."
- **No automatic decay or expiry** for memories that get superseded. Conflicting evidence competes at retrieval time instead, with the highest confidence winning, rather than one correction retroactively deleting another. Manual deletion (`DELETE /api/memories/{id}`) is the explicit "remove" mechanism.
- **Entity-type inference is a coarse heuristic**, just a handful of nearby cue words, used only as metadata and for the ambiguous-word gate. It's nowhere near a real NER model.
- **Single-user, SQLite only.** Multi-tenant or production use would need a `user_id` column and a real server-grade database. Out of scope here.
- **The tokenizer only treats letters and digits as part of a "word"** (`backend/tokenizer.py`). A period inside a canonical form, like a domain-style product name such as `Finn.no`, gets tokenized as two separate words and loses the period on substitution (`Finn.no` becomes `Finn no`). This was actually found during testing, not just assumed, see the next section. Digits inside a word (`Web3`, `KingSeW3`) work fine. Fixing the period case safely would mean telling apart a word-internal period from a sentence-ending one, which the formatter's terminal-punctuation logic doesn't currently need to do. Left as a known gap rather than a rushed, risky patch.

## Evaluation

Run it with `python eval/run_eval.py`, full setup is in `RUN.md`. Each of the 26 cases in `eval/dataset.jsonl` (16 categories, listed above) runs against a freshly reset database, so results never depend on what order they run in. Every case preserves its inputs, its expected result, the actual result, the full memory-table snapshot at that moment, and the per-span decision reasons. See `eval/results/report.md` for the committed baseline run: 26/26 passing, precision, recall, and F1 all at 1.0, p95 latency around 4ms, zero LLM calls or cost.

The harness sorts every span into `TP_useful_intervention`, `FP_unnecessary_intervention` or `FP_unexpected_intervention`, `FN_missed_intervention`, or `TN`. So useful interventions always get reported separately from unnecessary or incorrect ones, which the brief explicitly asks for, rather than everything getting folded into one pass/fail number.

## Optional: LLM-assisted eval scale-out

On top of the 26 hand-reasoned cases above, `tools/generate_entities.py` and `eval/simulate_users.py` use an LLM to stress the same two things, the memory extractor and live memory-based correction, at a bigger scale and with genuinely independent vocabulary. The LLM is never the judge of correctness here. This whole section is optional appendix material: `RUN.md`'s primary review path doesn't touch any of it and needs no credentials.

**What the LLM is (and isn't) trusted for.** `tools/generate_entities.py` calls the LLM only to brainstorm realistic mishearing-to-correction word pairs, things like `"chenai" -> "Chennai"` for a place, `"googel pixel" -> "Google Pixel"` for a product, `"krystopher" -> "Christopher"` for a person's name. There are 99 of them (42 people, 32 products, 25 places), written to the committed `eval/generated/entities_raw.jsonl`. It never gets asked to decide what the system should actually do with them.

**Provider history, told straight.** Three things happened here, in order:
1. First I tried getting the LLM to generate full conversation turns directly, asking for entire ASR/corrected pairs in one shot. That failed on the first model I tried. It couldn't keep an "asr" field and a "corrected" field distinct, it just echoed my few-shot examples back instead of writing anything new. So I moved sentence construction out of the LLM entirely (more on that below, under `eval/simulate_users.py`).
2. NVIDIA NIM was the first provider I used. Out of five models I spot-checked, only `nvidia/nemotron-3-ultra-550b-a55b` worked reliably enough to bother with, and even that endpoint was badly degraded under load during the actual generation run. Most calls either timed out or failed outright. `tools/llm_client.py`'s retry-with-incremental-save logic absorbed it fine, but a single batch of 8 could still take several minutes.
3. I switched to Mistral (`open-mistral-nemo`) once I had a working key for it, and it was dramatically faster (about 4 seconds a batch, no retries needed) and far more reliable (188 requests a minute versus NVIDIA's flaky 40). `tools/llm_client.py` now defaults to Mistral, and `KIVI_LLM_PROVIDER=nvidia` switches it back if you want. The tradeoff: Mistral's output needed more manual cleanup than NVIDIA's stronger model did. Roughly 20 of about 120 raw generated pairs got dropped by hand for being backwards, like `"mumbai" -> "Mumbay"`, which inverts which spelling is actually correct, or nonsensical, like `"delhi" -> "Delhi Metro"`, which is a different, unrelated entity rather than a mishearing of the same one. I'm recording that curation step here instead of hiding it, because an unfiltered LLM pool would have quietly fed wrong "ground truth" into the simulation.

**`eval/simulate_users.py`** takes those 99 entities and groups them into 33 simulated "users," three terms each. For every one of them, it:
1. Builds a roughly 10-turn conversation deterministically in Python. Fixed carrier-sentence templates per entity kind, with the term substituted into the `asr` field using its mishearing and into the `corrected` field using its canonical form, so it's correct by construction, plus a handful of ordinary filler sentences with no personal terms at all thrown in. Each of the persona's three terms gets mentioned a different number of times (1x, 2x, 3x) on purpose, so every single run exercises the low-confidence path, the just-activated path, and the reinforced-active path.
2. Resets the system and feeds that whole conversation through the real `POST /api/observe`, in order. This is the memory extractor actually being tested.
3. Reads back the real resulting memory state through `GET /api/memories`. That's ground truth, not a guess.
4. Builds one fresh follow-up sentence per term, using a template that wasn't used during teaching, so it's testing recall and not just repetition, and calls `POST /api/run`. This is live memory-based correction being tested.
5. Grades the result against the same documented rule used everywhere else in this README: an active memory has to correct with its stored canonical form, an inactive candidate must not, and something with no match must never intervene on ordinary filler text. That rule gets applied by whoever wrote the script, not re-derived from `decision.py`, so this isn't circular.

To run it yourself: `python tools/generate_entities.py` (needs `MISTRAL_KEY`, or `NVIDIA_KEY` with `KIVI_LLM_PROVIDER=nvidia`), then `python eval/simulate_users.py`, which needs nothing since it's just pure Python plus the already-committed entity pool, fully reproducible thanks to a fixed random seed. Results land in `eval/results/simulation_results.json` and `simulation_report.md`, with the full conversation transcripts, per-persona memory snapshots, and classifications. Every persona's session is individually inspectable.

**What it found: two real bugs, both fixed.**

1. **Digits were getting silently dropped.** A product name like `KingSeW3` got mangled by `backend/tokenizer.py`'s old letters-only word regex, which just lost the trailing digit. Neither the hand-written 26 cases nor the unit tests happened to cover this, because none of my hand-picked names had a digit in them. Fixed by letting the tokenizer allow digits after a word's first letter.
2. **A whole observation could get silently dropped for long matching sentences.** This one was worse. `backend/diff.py` merges a trailing word-insertion into the block immediately before it, so that expansions like `"apple" -> "Apple Inc"` still get learned as one pair. The bug was that it merged the insert into the *entire* preceding matched run, not just the one word next to it. For a short run like `"apple"`, just one word, that happened to work by accident. For a longer one, like `"meeting is scheduled in nassau"` fully matching before an inserted `"county"`, it produced one 5-word span, and the `MAX_SPAN_TOKENS` cap rejected that outright. So `nassau -> Nassau County` never got learned at all: no error, no memory row, just silence. I caught it because a single-word surface form showed `evidence_count=0` in the simulation report, which should never happen for a clean single-word correction. The fix only pulls in the one word right next to the insertion point now, leaving the rest of the matching run untouched. I verified it against both the new case and the original "apple" case, plus the full test suite and the primary eval, and nothing else broke.

The committed run, 99 entities, 33 personas, 99 recall checks, comes out to precision and recall both at 1.0, with zero false positives on ordinary filler text. There are 18 remaining flagged "anomalies," and I checked every one of them by reading the actual conversation logs in `eval/results/simulation_report.md`. They're all the same understood pattern, not a bug: when only part of a multi-word phrase is a genuine misspelling, like `san fransisco → San Francisco`, where "san"/"San" is just a re-casing and only "fransisco"/"Francisco" actually differs, the system correctly learns just the narrower sub-span, `fransisco → Francisco`, which is arguably more useful memory since it now fixes that word anywhere, not only right after "san." The simulation script's own bookkeeping tracks mentions by the full LLM-generated phrase, so it flags that as a mismatch even though the underlying behavior is exactly right.

## AI use

This project was built with Claude Code (Anthropic). An initial research report (`../deep-research-report.md`, outside this repo) explored the design space first. A plan built from that report, plus a direct read of the assignment PDF, is what this repository actually implements, and quite a few of the report's original choices got revised along the way during implementation: the diff/formatter split, the insert-merge fix, localized entity-type inference, the deterministic-vs-LLM tradeoff, and the concrete decision rules. Those changes came from hand-verifying actual behavior against the brief's example and the eval cases, not from writing code first and cherry-picking whatever passed afterward. All the code, tests, the eval dataset, and this README got written and checked iteratively in this session. Every behavior documented above, including the evaluation numbers that say "already run and passing," was actually executed and checked, not just asserted from memory.
