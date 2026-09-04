# Kivi Memory System - Evaluation Report

Run at: 2026-09-04T12:25:34Z

**26 / 26 cases passed.**

## Overall

- Precision: 1.0
- Recall: 1.0
- F1: 1.0

- Useful interventions (TP): 22
- Unnecessary/incorrect interventions (FP): 0
- Missed interventions (FN): 0
- Correct non-interventions (TN): 4

## By Category

| Category | Cases | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|
| already_correct_input | 2/2 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 2 |
| ambiguous_common_word | 3/3 | 1.0 | 1.0 | 1.0 | 2 | 0 | 0 | 1 |
| case_sensitivity | 2/2 | 1.0 | 1.0 | 1.0 | 2 | 0 | 0 | 0 |
| conflicting_evidence | 1/1 | 1.0 | 1.0 | 1.0 | 1 | 0 | 0 | 0 |
| fuzzy_typo_exceeds_budget | 2/2 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 0 |
| fuzzy_typo_within_budget | 1/1 | 1.0 | 1.0 | 1.0 | 1 | 0 | 0 | 0 |
| low_confidence_no_intervene | 1/1 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 1 |
| multiple_memories_same_sentence | 1/1 | 1.0 | 1.0 | 1.0 | 2 | 0 | 0 | 0 |
| multiword_entities | 2/2 | 1.0 | 1.0 | 1.0 | 3 | 0 | 0 | 0 |
| name_and_product | 1/1 | 1.0 | 1.0 | 1.0 | 3 | 0 | 0 | 0 |
| personal_names | 1/1 | 1.0 | 1.0 | 1.0 | 1 | 0 | 0 | 0 |
| possessive_forms | 2/2 | 1.0 | 1.0 | 1.0 | 2 | 0 | 0 | 0 |
| product_names | 1/1 | 1.0 | 1.0 | 1.0 | 1 | 0 | 0 | 0 |
| punctuation_adjacent_tokens | 3/3 | 1.0 | 1.0 | 1.0 | 3 | 0 | 0 | 0 |
| repeated_confirmation | 1/1 | 1.0 | 1.0 | 1.0 | 1 | 0 | 0 | 0 |
| unseen_terms | 2/2 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 0 |

## Latency

- p50: 3.381ms, p95: 4.967ms, max: 7.367ms
- SLA: p95 < 50.0ms -> MET

## Database Growth

| Observations fed | Memory rows |
|---|---|
| 10 | 6 |
| 25 | 6 |
| 50 | 7 |
| 93 | 8 |

## Model Usage / Cost

- N/A - the default formatter is rule-based; no LLM calls occur in this configuration.

## Failures (0)

None.