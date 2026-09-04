"""Derive (observed_form, canonical_form) memory candidates from an
observation: an ASR transcript plus the user's corrected version.

We diff the FORMATTED baseline (not the raw ASR) against the correction, so
that generic capitalization/punctuation the formatter already owns never
pollutes memory - only the personal-term corrections left over after
formatting are learned. Sentence-initial re-casing with no spelling change is
skipped for the same reason (the formatter already capitalizes the first word
of every sentence). Mid-sentence re-casing with no spelling change IS learned:
the formatter (see backend/formatter.py) deliberately does not guess that a
lowercase mid-sentence word is a proper noun, so a user capitalizing one
("sohail" -> "Sohail") is exactly the personal-term signal memory exists to
capture, not formatting's job.
"""
import difflib
from dataclasses import dataclass

from backend import config
from backend.formatter import format as format_text
from backend.tokenizer import Token, tokenize

PERSON_CUES = {"ask", "call", "email", "tell", "remind", "meet", "said", "told", "hi", "hey"}
PRODUCT_CUES = {"service", "app", "device", "software", "product", "platform", "update", "install"}
_CONTEXT_WINDOW = 4


def _infer_entity_type(c_tokens: list[Token], j1: int, j2: int) -> str:
    """Localized heuristic: look only at words near this specific span, not
    the whole sentence, so one product-flavoured sentence doesn't mislabel
    every person's name it also happens to mention."""
    before = c_tokens[max(0, j1 - _CONTEXT_WINDOW) : j1]
    after = c_tokens[j2 : j2 + _CONTEXT_WINDOW]
    nearby_norms = {t.norm for t in before + after}
    if nearby_norms & PRODUCT_CUES:
        return "product"
    if nearby_norms & PERSON_CUES:
        return "person"
    return "other"


def _is_sentence_initial(text: str, start: int) -> bool:
    """True if the character at `start` is the first letter of a sentence
    in `text` (position 0, or preceded only by whitespace after [.!?])."""
    i = start - 1
    while i >= 0 and text[i].isspace():
        i -= 1
    return i < 0 or text[i] in ".!?"


@dataclass
class ObservationPair:
    observed_form: str     # normalized (lowercase), space-joined for multi-word spans
    canonical_form: str     # casing preserved from the corrected text
    token_count: int
    entity_type: str


def extract_observations(asr_text: str, corrected_text: str) -> tuple[list[ObservationPair], str]:
    formatted = format_text(asr_text)
    f_tokens = tokenize(formatted)
    c_tokens = tokenize(corrected_text)

    f_norms = [t.norm for t in f_tokens]
    c_norms = [t.norm for t in c_tokens]

    matcher = difflib.SequenceMatcher(a=f_norms, b=c_norms, autojunk=False)
    raw_ops = matcher.get_opcodes()

    # Merge a trailing "insert" into the immediately preceding block so that
    # pure expansions like "apple" -> "Apple Inc" - an insert right after an
    # equal token, not a same-length replace - are still learned as a single
    # (observed, canonical) pair instead of being silently dropped.
    #
    # Only the LAST token of a preceding "equal" block is pulled in as the
    # anchor - not the whole block. Merging the entire equal run is wrong
    # whenever that run is long (e.g. "meeting is scheduled in nassau" all
    # matching before an inserted "county" would otherwise produce one
    # 5-word replace span that MAX_SPAN_TOKENS then rejects outright,
    # silently dropping the observation instead of learning "nassau" ->
    # "Nassau County"). "delete" (a word removed outright) stays unhandled -
    # out of scope for this assignment's word-level memory.
    merged_ops: list[tuple[str, int, int, int, int]] = []
    for tag, i1, i2, j1, j2 in raw_ops:
        if tag == "insert" and merged_ops and merged_ops[-1][2] == i1 and merged_ops[-1][0] != "delete":
            ptag, pi1, pi2, pj1, pj2 = merged_ops[-1]
            if ptag == "equal" and pi2 > pi1:
                merged_ops[-1] = ("equal", pi1, pi2 - 1, pj1, pj2 - 1)
                merged_ops.append(("replace", pi2 - 1, pi2, pj2 - 1, j2))
            else:
                merged_ops[-1] = ("replace", pi1, pi2, pj1, j2)
        else:
            merged_ops.append((tag, i1, i2, j1, j2))

    pairs: list[ObservationPair] = []

    for tag, i1, i2, j1, j2 in merged_ops:
        if tag == "equal":
            # SequenceMatcher compares lowercase norms, so a pure-casing
            # change (e.g. "priya" -> "Priya") never produces a "replace" op
            # - it looks identical to the matcher. Scan matched pairs here to
            # catch that case: same norm, different base casing, mid-sentence.
            # A recasing token next to an unrelated replace (e.g. "sarvam"
            # right before "kiwi" -> "Kivi") is learned as its own entry, same
            # as one next to a replace it's semantically part of (e.g. "new"
            # before "yolk sity" -> "York City") - the diff alone can't tell
            # those apart without real entity extraction (future work: see
            # README). Either way the combined substitutions still produce
            # the correct final sentence; they just land as separate memories
            # instead of one multi-word one.
            for offset in range(i2 - i1):
                f_tok, c_tok = f_tokens[i1 + offset], c_tokens[j1 + offset]
                if f_tok.base == c_tok.base or _is_sentence_initial(formatted, f_tok.start):
                    continue
                pairs.append(
                    ObservationPair(
                        observed_form=f_tok.norm,
                        canonical_form=c_tok.base,
                        token_count=1,
                        entity_type=_infer_entity_type(c_tokens, j1 + offset, j1 + offset + 1),
                    )
                )
            continue
        if tag != "replace":
            continue
        obs_tokens: list[Token] = f_tokens[i1:i2]
        can_tokens: list[Token] = c_tokens[j1:j2]
        if not obs_tokens or not can_tokens:
            continue
        if len(obs_tokens) > config.MAX_SPAN_TOKENS or len(can_tokens) > config.MAX_SPAN_TOKENS:
            continue  # skip large rewrites - this is word memory, not sentence memory

        observed_form = " ".join(t.norm for t in obs_tokens)
        canonical_form = " ".join(t.base for t in can_tokens)

        if observed_form == canonical_form.lower() and _is_sentence_initial(formatted, obs_tokens[0].start):
            continue  # sentence-initial re-casing - the formatter already does this

        pairs.append(
            ObservationPair(
                observed_form=observed_form,
                canonical_form=canonical_form,
                token_count=len(obs_tokens),
                entity_type=_infer_entity_type(c_tokens, j1, j2),
            )
        )

    return pairs, formatted
