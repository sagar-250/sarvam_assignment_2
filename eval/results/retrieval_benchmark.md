# Retrieval Performance Benchmark

Compares backend.retrieval.retrieve() (routes to an in-memory strategy below 2,000 memory rows, and an indexed+SymSpell strategy above it) against a reimplementation of the original algorithm with no router - always a full-table load, then a Levenshtein scan against every single-token row per query token.

All times are per-batch (see column headers), averaged over 3 repeats, on a freshly built in-memory SQLite DB per size.

## retrieve() vs. no-router legacy baseline

| Memory rows | Path used | New full retrieve /5 transcripts (ms) | Legacy full retrieve /5 transcripts (ms) | Speedup |
|---|---|---|---|---|
| 100 | small | 8.2672 | 4.2231 | 0.5x |
| 1,000 | small | 43.8405 | 36.3487 | 0.8x |
| 5,000 | large | 8.019 | 212.1971 | 26.5x |
| 20,000 | large | 12.8364 | 962.3721 | 75.0x |
| 50,000 | large | 23.4162 | 2482.4011 | 106.0x |

## Step-by-step (new implementation)

| Memory rows | Path | Cold SymSpell build (ms) | Exact-match step (ms) | Fuzzy-match step /6 (ms) |
|---|---|---|---|---|
| 100 | small | n/a (small-table path) | 0.0016 | 0.1827 |
| 1,000 | small | n/a (small-table path) | 0.0015 | 1.7125 |
| 5,000 | large | 225.2863 | 0.9026 | 0.0604 |
| 20,000 | large | 811.0137 | 0.804 | 0.049 |
| 50,000 | large | 2639.2569 | 0.8875 | 0.0798 |

## Legacy (no-router) baseline

| Memory rows | Full-table load (ms) | Fuzzy scan /6 (ms) | Full retrieve /5 transcripts (ms) |
|---|---|---|---|
| 100 | 0.8445 | 0.1946 | 4.2231 |
| 1,000 | 5.3401 | 1.7453 | 36.3487 |
| 5,000 | 53.7117 | 8.9067 | 212.1971 |
| 20,000 | 283.6541 | 41.2379 | 962.3721 |
| 50,000 | 715.4978 | 100.1051 | 2482.4011 |

Note: "cold SymSpell build" only happens once per DB engine per change to the single-token dictionary (see backend/retrieval.py's fingerprint cache), and only on the large-table path - it is not paid on every request, and not paid at all below the router threshold.
