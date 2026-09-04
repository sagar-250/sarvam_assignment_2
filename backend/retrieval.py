"""Candidate lookup: exact + fuzzy matching of memory entries against a
tokenized transcript, including multi-word spans.

Returns candidates regardless of `active` status - inactive/low-confidence
matches are still surfaced so decision.py can explain *why* nothing happened
for a term the system has partially seen before.
"""
from dataclasses import dataclass

from rapidfuzz.distance import Levenshtein
from sqlalchemy.orm import Session

from backend import config
from backend.models import Memory
from backend.tokenizer import Token, span_norm


@dataclass
class Candidate:
    start_idx: int
    end_idx: int  # exclusive
    memory: Memory
    match_type: str  # "exact" | "fuzzy"
    edit_distance: int


def _fuzzy_budget(length: int) -> int:
    if length <= 4:
        return 0
    if length <= 7:
        return 1
    return 2


def retrieve(session: Session, tokens: list[Token]) -> list[Candidate]:
    if not tokens:
        return []

    all_memories = session.query(Memory).all()
    by_token_count: dict[int, list[Memory]] = {}
    for m in all_memories:
        by_token_count.setdefault(m.token_count, []).append(m)

    n = len(tokens)
    claimed: set[int] = set()
    candidates: list[Candidate] = []

    for start in range(n):
        if start in claimed:
            continue
        max_len = min(config.MAX_SPAN_TOKENS, n - start)
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
                    best_distance = None
                    fuzzy_rows: list[Memory] = []
                    for row in by_token_count.get(1, []):
                        dist = Levenshtein.distance(norm, row.observed_form)
                        if 0 < dist <= budget:
                            if best_distance is None or dist < best_distance:
                                best_distance = dist
                                fuzzy_rows = [row]
                            elif dist == best_distance:
                                fuzzy_rows.append(row)
                    if fuzzy_rows:
                        for row in fuzzy_rows:
                            candidates.append(Candidate(start, start + 1, row, "fuzzy", best_distance))
                        claimed.add(start)
                        matched_here = True
                        break
        if not matched_here:
            continue

    return candidates
