"""Candidate lookup: exact + fuzzy matching of memory entries against a
tokenized transcript, including multi-word spans.

Returns candidates regardless of `active` status - inactive/low-confidence
matches are still surfaced so decision.py can explain *why* nothing happened
for a term the system has partially seen before.

Scaling: two strategies, routed by table size (config.RETRIEVAL_SMALL_TABLE_
THRESHOLD - see eval/benchmark_retrieval.py for the measured crossover this
is based on):

- Small tables: one bulk load, then pure in-memory matching (the original
  design). Below the threshold, building/caching an index costs more than it
  saves - a handful of DB round trips and a Python list scan are already fast.
- Large tables: exact matches are batched into one indexed SQL query per
  span length actually present in the transcript (uses ix_memory_token_
  observed), not one query per span attempted, and not a full-table load.
  Fuzzy matches use a symmetric-delete (SymSpell-style) index instead of a
  Levenshtein comparison against every single-token row: candidates come from
  O(1) dict lookups on precomputed delete-variants, and only that small
  candidate set is verified with real Levenshtein distance. The index is
  cached per DB engine and rebuilt only when the single-token dictionary
  actually changes (cheap COUNT/MAX fingerprint, no full-table read on
  cache hits).
"""
import weakref
from dataclasses import dataclass
from typing import Callable

from rapidfuzz.distance import Levenshtein
from sqlalchemy import func
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


ExactLookupFn = Callable[[int, str], list[Memory]]
FuzzyLookupFn = Callable[[str, int], "tuple[list[Memory], int] | None"]


def _brute_force_fuzzy(norm: str, budget: int, rows: list[Memory]) -> "tuple[list[Memory], int] | None":
    """Levenshtein against every candidate row, keeping only the row(s) at
    the single smallest distance within budget. Fine when `rows` is small
    (small-table path); this is exactly what gets slow at scale, which is
    what the SymSpell index below exists to avoid."""
    best_distance = None
    best_rows: list[Memory] = []
    for row in rows:
        dist = Levenshtein.distance(norm, row.observed_form)
        if 0 < dist <= budget:
            if best_distance is None or dist < best_distance:
                best_distance = dist
                best_rows = [row]
            elif dist == best_distance:
                best_rows.append(row)
    if best_distance is None:
        return None
    return best_rows, best_distance


def _retrieve_core(tokens: list[Token], exact_lookup: ExactLookupFn, fuzzy_lookup: FuzzyLookupFn) -> list[Candidate]:
    """Span-selection/claiming logic shared by both strategies - they differ
    only in how exact_lookup/fuzzy_lookup are backed (in-memory dict + brute
    force vs. batched indexed query + SymSpell)."""
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

            exact_rows = exact_lookup(span_len, norm)
            if exact_rows:
                for row in exact_rows:
                    candidates.append(Candidate(start, start + span_len, row, "exact", 0))
                claimed.update(range(start, start + span_len))
                matched_here = True
                break

            if span_len == 1:
                budget = _fuzzy_budget(len(norm))
                if budget > 0:
                    result = fuzzy_lookup(norm, budget)
                    if result is not None:
                        rows, best_distance = result
                        for row in rows:
                            candidates.append(Candidate(start, start + 1, row, "fuzzy", best_distance))
                        claimed.add(start)
                        matched_here = True
                        break
        if not matched_here:
            continue

    return candidates


# ---------------------------------------------------------------------------
# Small-table strategy: one bulk load, then in-memory matching.
# ---------------------------------------------------------------------------


def _retrieve_small(session: Session, tokens: list[Token]) -> list[Candidate]:
    all_memories = session.query(Memory).all()
    by_key: dict[tuple[int, str], list[Memory]] = {}
    single_token_rows: list[Memory] = []
    for m in all_memories:
        by_key.setdefault((m.token_count, m.observed_form), []).append(m)
        if m.token_count == 1:
            single_token_rows.append(m)

    def exact_lookup(span_len: int, norm: str) -> list[Memory]:
        return by_key.get((span_len, norm), [])

    def fuzzy_lookup(norm: str, budget: int):
        return _brute_force_fuzzy(norm, budget, single_token_rows)

    return _retrieve_core(tokens, exact_lookup, fuzzy_lookup)


# ---------------------------------------------------------------------------
# Large-table strategy: batched indexed exact match + cached SymSpell fuzzy.
# ---------------------------------------------------------------------------

# Highest value _fuzzy_budget can ever return - the dictionary side of the
# symmetric-delete index is built to this distance so it's always a superset
# of whatever a query needs, regardless of that query's own (smaller) budget.
_SYMSPELL_MAX_EDIT = 2


def _delete_variants(word: str, max_dist: int) -> set[str]:
    """All strings reachable from `word` by deleting 0..max_dist characters."""
    variants = {word}
    frontier = {word}
    for _ in range(max_dist):
        next_frontier: set[str] = set()
        for w in frontier:
            for i in range(len(w)):
                next_frontier.add(w[:i] + w[i + 1 :])
        next_frontier -= variants
        if not next_frontier:
            break
        variants |= next_frontier
        frontier = next_frontier
    return variants


class _SymSpellIndex:
    """Symmetric-delete index over single-token memory entries, for
    edit-distance-bounded lookup without scanning every row."""

    def __init__(self, rows: list[Memory]):
        self.word_to_rows: dict[str, list[Memory]] = {}
        for row in rows:
            self.word_to_rows.setdefault(row.observed_form, []).append(row)

        self._deletes_index: dict[str, set[str]] = {}
        for word in self.word_to_rows:
            for variant in _delete_variants(word, _SYMSPELL_MAX_EDIT):
                self._deletes_index.setdefault(variant, set()).add(word)

    def lookup(self, query: str, budget: int) -> "tuple[list[Memory], int] | None":
        """Rows at the single smallest edit distance within `budget`, mirroring
        _brute_force_fuzzy's tie-break (only the closest match(es), not every
        row within budget)."""
        if budget <= 0 or not self.word_to_rows:
            return None

        candidate_words: set[str] = set()
        for variant in _delete_variants(query, budget):
            candidate_words |= self._deletes_index.get(variant, set())

        best_distance = None
        best_words: list[str] = []
        for word in candidate_words:
            dist = Levenshtein.distance(query, word)
            if 0 < dist <= budget:
                if best_distance is None or dist < best_distance:
                    best_distance = dist
                    best_words = [word]
                elif dist == best_distance:
                    best_words.append(word)

        if best_distance is None:
            return None
        rows = [row for word in best_words for row in self.word_to_rows[word]]
        return rows, best_distance


# Keyed by engine object (weakly) rather than id() - engine ids get reused
# after garbage collection (e.g. between tests with fresh :memory: DBs),
# which would otherwise risk a stale cache hit against an unrelated DB.
_symspell_cache: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def _single_token_fingerprint(session: Session) -> tuple:
    """Cheap aggregate query (count + max id) to detect whether the
    single-token dictionary changed, without reading any row data."""
    return session.query(
        func.count(Memory.id), func.max(Memory.id)
    ).filter(Memory.token_count == 1).one()


def _get_symspell(session: Session) -> _SymSpellIndex:
    engine = session.get_bind()
    fingerprint = _single_token_fingerprint(session)

    cached = _symspell_cache.get(engine)
    if cached is not None and cached[0] == fingerprint:
        return cached[1]

    rows = session.query(Memory).filter(Memory.token_count == 1).all()
    index = _SymSpellIndex(rows)
    _symspell_cache[engine] = (fingerprint, index)
    return index


def _collect_spans(tokens: list[Token]) -> list[tuple[int, str]]:
    """Every (span_len, norm) the core loop might ask for, ignoring claiming
    (that's resolved later, in _retrieve_core) - used only to know what to
    batch-fetch up front."""
    n = len(tokens)
    spans: list[tuple[int, str]] = []
    for start in range(n):
        max_len = min(config.MAX_SPAN_TOKENS, n - start)
        for span_len in range(1, max_len + 1):
            spans.append((span_len, span_norm(tokens[start : start + span_len])))
    return spans


def _batched_exact_lookup(session: Session, spans: list[tuple[int, str]]) -> dict[tuple[int, str], list[Memory]]:
    """One indexed query per distinct span length present in the transcript
    (at most config.MAX_SPAN_TOKENS queries total), instead of one query per
    (start, span_len) attempt - keeps retrieve() to a handful of DB round
    trips regardless of transcript length."""
    norms_by_len: dict[int, set[str]] = {}
    for span_len, norm in spans:
        norms_by_len.setdefault(span_len, set()).add(norm)

    result: dict[tuple[int, str], list[Memory]] = {}
    for span_len, norms in norms_by_len.items():
        rows = (
            session.query(Memory)
            .filter(Memory.token_count == span_len, Memory.observed_form.in_(norms))
            .all()
        )
        for row in rows:
            result.setdefault((span_len, row.observed_form), []).append(row)
    return result


def _retrieve_large(session: Session, tokens: list[Token]) -> list[Candidate]:
    exact_index = _batched_exact_lookup(session, _collect_spans(tokens))
    symspell_box: list[_SymSpellIndex] = []  # lazy - only built if fuzzy is actually needed

    def exact_lookup(span_len: int, norm: str) -> list[Memory]:
        return exact_index.get((span_len, norm), [])

    def fuzzy_lookup(norm: str, budget: int):
        if not symspell_box:
            symspell_box.append(_get_symspell(session))
        return symspell_box[0].lookup(norm, budget)

    return _retrieve_core(tokens, exact_lookup, fuzzy_lookup)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def _memory_count(session: Session) -> int:
    """COUNT(*) rather than a LIMIT-and-measure probe: a probe would need to
    hydrate full Memory rows to be reusable by _retrieve_small, and hydrating
    threshold+1 rows only to discard them on the large-table path (the more
    performance-sensitive one) costs far more than it saves on the small one."""
    return session.query(func.count(Memory.id)).scalar() or 0


def retrieve(session: Session, tokens: list[Token]) -> list[Candidate]:
    if not tokens:
        return []

    if _memory_count(session) <= config.RETRIEVAL_SMALL_TABLE_THRESHOLD:
        return _retrieve_small(session, tokens)
    return _retrieve_large(session, tokens)
