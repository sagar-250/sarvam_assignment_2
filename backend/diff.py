"""Derive (observed_form, canonical_form) memory candidates by diffing the
FORMATTED baseline (not raw ASR) against the user's correction, so generic
formatting noise never pollutes memory - only the personal-term corrections
left over after formatting get learned."""
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

    # Merge a trailing "insert" into just the last token of the preceding
    # "equal" block, so expansions like "apple" -> "Apple Inc" get learned as
    # one pair. Pulling in the whole equal run instead (not just the last
    # token) would blow past MAX_SPAN_TOKENS on longer sentences and silently
    # drop the observation.
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
            # change ("priya" -> "Priya") looks identical to it - scan
            # matched pairs here to catch that case separately.
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
