"""Decide, for each retrieved candidate, whether to intervene - and produce a
human-readable reason either way. This is what makes every decision (applied
or not) explainable, per the assignment's "understand why the system did or
did not intervene" requirement.

Concrete rules, applied in order:
  1. Already-correct guard - span already matches the canonical form.
  2. Confidence gate - candidate memory must be `active` (evidence_count >= 2
     and confidence >= 0.6).
  3. Ambiguous-common-word context gate - a small, deliberately curated set of
     words that are ALSO ordinary dictionary words (e.g. "apple") require a
     nearby supporting cue before a specialized meaning is applied. This list
     is intentionally small and hand-curated rather than a full dictionary:
     a full dictionary would gate too aggressively and block ordinary product
     names that happen to be real words (e.g. "kiwi") - documented as a
     limitation in README.
  4. Conflicting candidates - if multiple active rows match the same span
     with different canonical forms, the highest-confidence one wins and the
     explanation says so.
"""
from dataclasses import dataclass

from backend import config
from backend.models import Memory
from backend.retrieval import Candidate
from backend.tokenizer import Token, span_norm

# Deliberately small: only entries here get the extra "needs supporting
# context" gate. Everything else (e.g. "kiwi") only needs the confidence gate.
COMMON_WORD_CUES: dict[str, dict] = {
    "apple": {
        "cues": {"inc", "ceo", "company", "stock", "release", "update", "iphone", "macbook"},
        "entity_types": ("company", "product", "other"),
    },
}


@dataclass
class Decision:
    start_idx: int
    end_idx: int
    kind: str  # "intervene" | "no_intervene"
    span_text: str
    memory_id: int | None
    observed_form: str | None
    canonical_form: str | None  # value to apply, only set when kind == "intervene"
    entity_type: str | None
    match_type: str | None
    edit_distance: int | None
    confidence: float | None
    evidence_count: int | None
    reason: str
    explanation: str


def _context_tokens(tokens: list[Token], start_idx: int, end_idx: int) -> list[Token]:
    before = tokens[max(0, start_idx - config.CONTEXT_WINDOW) : start_idx]
    after = tokens[end_idx : end_idx + config.CONTEXT_WINDOW]
    return before + after


def decide(tokens: list[Token], candidates: list[Candidate]) -> list[Decision]:
    groups: dict[tuple[int, int], list[Candidate]] = {}
    for c in candidates:
        groups.setdefault((c.start_idx, c.end_idx), []).append(c)

    decisions: list[Decision] = []

    for (start_idx, end_idx), group in sorted(groups.items()):
        rows: list[Memory] = [c.memory for c in group]
        match_type = group[0].match_type
        edit_distance = group[0].edit_distance
        span_tokens = tokens[start_idx:end_idx]
        span_text = " ".join(t.text for t in span_tokens)
        span_base_text = " ".join(t.base for t in span_tokens)
        window_norm = span_norm(span_tokens)

        active_rows = [r for r in rows if r.active]
        conflicting = len(active_rows) > 1
        if active_rows:
            best = max(active_rows, key=lambda r: (r.confidence, r.last_updated))
        else:
            best = max(rows, key=lambda r: (r.confidence, r.last_updated))

        base_kwargs = dict(
            start_idx=start_idx,
            end_idx=end_idx,
            span_text=span_text,
            memory_id=best.id,
            observed_form=best.observed_form,
            entity_type=best.entity_type,
            match_type=match_type,
            edit_distance=edit_distance,
            confidence=best.confidence,
            evidence_count=best.evidence_count,
        )

        # Case-sensitive: a memory can be a pure re-casing correction (e.g.
        # "priya" -> "Priya"), so a lowercase-normalized comparison here would
        # always call it "already correct" and the casing would never apply.
        if span_base_text == best.canonical_form:
            decisions.append(
                Decision(
                    kind="no_intervene",
                    canonical_form=None,
                    reason="already_correct",
                    explanation=f"'{span_text}' already matches the canonical form '{best.canonical_form}'.",
                    **base_kwargs,
                )
            )
            continue

        if not best.active:
            decisions.append(
                Decision(
                    kind="no_intervene",
                    canonical_form=None,
                    reason="below_confidence_threshold",
                    explanation=(
                        f"'{span_text}' matches a candidate memory (#{best.id}) but it is not yet "
                        f"trusted (evidence_count={best.evidence_count}, confidence={best.confidence:.2f} "
                        f"< {config.MIN_CONFIDENCE_ACTIVE:.2f}); left unchanged."
                    ),
                    **base_kwargs,
                )
            )
            continue

        cue_cfg = COMMON_WORD_CUES.get(best.observed_form)
        if cue_cfg and best.entity_type in cue_cfg["entity_types"]:
            nearby_norms = {t.norm for t in _context_tokens(tokens, start_idx, end_idx)}
            if not (nearby_norms & cue_cfg["cues"]):
                decisions.append(
                    Decision(
                        kind="no_intervene",
                        canonical_form=None,
                        reason="ambiguous_common_word_no_supporting_context",
                        explanation=(
                            f"'{span_text}' matches memory #{best.id} ({best.entity_type}, "
                            f"confidence {best.confidence:.2f}) but no supporting context word was "
                            f"found nearby; left unchanged to avoid a false correction."
                        ),
                        **base_kwargs,
                    )
                )
                continue

        explanation = (
            f"Replaced '{span_text}' with '{best.canonical_form}' (memory #{best.id}, "
            f"confidence {best.confidence:.2f}, {best.evidence_count} observations)."
        )
        if conflicting:
            explanation += " Multiple candidate corrections existed; chose the highest-confidence one."

        decisions.append(
            Decision(
                kind="intervene",
                canonical_form=best.canonical_form,
                reason="active_memory_high_confidence",
                explanation=explanation,
                **base_kwargs,
            )
        )

    return decisions
