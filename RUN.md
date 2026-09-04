# RUN.md

**Primary review method: completely local application.** No hosted URL, no external services, no credentials required.

## 1. Required runtimes and versions

- Python 3.11 or newer (developed and tested on 3.12.3)
- No other runtime required (frontend is static HTML/JS, served by the Python backend — no Node/npm needed)

## 2. Environment variables

None are required. See `.env.example` for optional tuning knobs (all have sane defaults) — none of them need to be set for review. There is no LLM key requirement anywhere in the primary path.

## 3. Install dependencies

From the repository root (`kivi-memory/`):

```
python -m venv .venv
```

Windows (PowerShell/cmd):
```
.venv\Scripts\activate
```
macOS/Linux:
```
source .venv/bin/activate
```

Then:
```
pip install -r requirements.txt
```

**Optional, not required for steps 1-10 below:** the "Bulk Teach" UI's "Corrected text only" mode uses spaCy for offline, credential-free entity extraction. One-time, no API key, just a ~13MB model download:
```
python -m spacy download en_core_web_sm
```
If skipped, that specific mode still returns a clear per-item message rather than failing silently; nothing else in the app is affected.

## 4. Create, migrate, and seed the database

```
python scripts/init_db.py
python scripts/seed.py
```

`init_db.py` creates `data/kivi_memory.db` with the `memory` and `evidence` tables (idempotent — safe to run again). `seed.py` loads `data/seed_observations.jsonl` (5 people/products/places, each confirmed twice, plus "new" -> "New" as a separate mid-sentence recasing memory learned alongside the "new yolk sity" -> "New York City" observation — see README "Limitations") so the Memory State table isn't empty on first load: 6 rows total.

## 5. Start the process

```
uvicorn backend.app:app --port 8000
```

(A single process serves both the API and the static frontend — nothing else needs to be started.)

## 6. URL to open

http://localhost:8000/

## 7. Primary interactions to try

1. Look at **Memory State** — 6 seeded memories should already be listed as `active`.
2. In **Try a Transcript**, paste the assignment's own example and click Run:
   `ask aditya to review the sarvam kiwi service`
   Expect memory-aware output: `Ask Aaditya to review the sarvam Kivi service.` ("sarvam" stays lowercase only because it was never taught — it isn't in the seed data, not because casing-only corrections are unlearnable; teach it via step 4's flow and it will start being corrected too), with an Explanation panel showing which memories were used and why.
3. Try an **ambiguous word**: `i ate a whole apple for lunch` → left unchanged (no supporting context). Then `apple confirmed the company stock update today` → corrected to `Apple Inc` (context cues present). This shows the same memory being deliberately applied in one case and withheld in the other.
4. In **Teach Kivi**, submit a brand-new correction once (e.g. ASR `call rohan now`, corrected `Call Rohan now`) — it becomes a `candidate`, not yet `active`, in the Memory State table. Submit the identical pair a second time — it flips to `active`. Then run a transcript containing "rohan" to see it get applied only after the second confirmation.
5. Click **Reset system** — confirms, clears all memory, and the Memory State table goes empty. Re-run step 4 to see the journey repeat from scratch.

**Extra, not required for review:** **Bulk Teach** (section 4 of the UI) has two modes, so you can use whichever form your historical data is in:
- **"Corrected pairs"** (always available, no credentials) — paste many `(asr, corrected)` pairs at once as JSONL, one JSON object per line, e.g. `{"asr": "call rohan now", "corrected": "Call Rohan now"}` repeated twice teaches and activates "rohan" -> "Rohan" in a single submission. A thin, fully deterministic loop over the same `learn()` path step 4 already exercises (`POST /api/observe/bulk`) — no LLM, no schema change.
- **"Corrected text only"** — paste one or more already-correct conversation transcripts (no raw ASR side at all), separated by a blank line (`POST /api/learn-from-conversations`). A free, offline spaCy NER pass (needs the one-time model download above) always runs first; if `MISTRAL_KEY`/`NVIDIA_KEY` is also configured, an LLM pass refines the result and catches names NER's generic model tends to miss (see README for a verified example). Neither is required for the other to work — with only the NER model installed, this mode already works with zero LLM credentials; each result shows `sources: ["ner"]`/`["llm"]`/`["ner","llm"]` so you can see which pass actually found each entity.

## 8. Exact command to run the evaluation

```
python eval/run_eval.py
```

## 9. Where results are written

- `eval/results/results.json` — full machine-readable results (per-case inputs, expected/actual output, memory-state snapshot, per-span decision reasons, latency, DB growth, model usage).
- `eval/results/report.md` — human-readable summary (per-category precision/recall/F1, latency, DB growth, and full detail on any failing case).

Both are committed to the repository with the results of the last verified run (26/26 cases passing). Re-running regenerates them in place.

## 10. Exact procedure for resetting the system

Any of the following:
- Click **Reset system** in the UI (calls `POST /api/reset`).
- `curl -X POST http://localhost:8000/api/reset`
- Delete `data/kivi_memory.db` and re-run `python scripts/init_db.py` (and optionally `python scripts/seed.py`) for a completely fresh database file.

---

### Running tests (optional, not part of the primary review path)

```
python -m pytest tests/ -q
```

62 unit/integration tests covering the tokenizer, diff logic, memory lifecycle, retrieval, decision rules, grouping, NER extraction, LLM entity extraction, and the API layer.

### Multi-user simulation (optional, not part of the primary review path)

```
python eval/simulate_users.py
```

Needs no credentials — it replays an already-committed, LLM-sourced entity pool (`eval/generated/entities_raw.jsonl`) through 33 simulated user sessions with a fixed random seed (fully reproducible). Writes `eval/results/simulation_report.md` / `simulation_results.json`. See README "Optional: LLM-assisted eval scale-out" for what this tests and what it found. Regenerating the entity pool itself (`python tools/generate_entities.py`) needs `MISTRAL_KEY` (or `NVIDIA_KEY` with `KIVI_LLM_PROVIDER=nvidia`) and is not required to run the simulation against the committed pool.
