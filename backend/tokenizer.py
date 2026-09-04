"""Word tokenization that preserves enough information (character offsets,
original casing, possessive suffixes) to losslessly reconstruct the source
string after substituting a subset of tokens.
"""
import re
from dataclasses import dataclass

# A "word" must start with a letter (so bare numbers/times/dates are never
# swept in as tokens) but may contain digits after that, since real product
# names commonly do (e.g. "Web3", "GPT4"). A trailing 's/'s (curly or
# straight) is captured as a possessive suffix, not part of the base word.
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:['\u2019][A-Za-z]+)?")
_APOS_CHARS = ("'", "\u2019")


@dataclass
class Token:
    text: str          # raw matched text, e.g. "Aditya's"
    base: str           # word without possessive suffix, casing preserved, e.g. "Aditya"
    norm: str            # lowercase base, used for matching, e.g. "aditya"
    start: int             # char offset in source string (inclusive)
    end: int                # char offset in source string (exclusive)
    is_possessive: bool
    possessive_suffix: str  # "'s" / "\u2019s" / ""


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    for m in _WORD_RE.finditer(text):
        raw = m.group(0)
        start, end = m.start(), m.end()

        apos_idx = -1
        for ch in _APOS_CHARS:
            idx = raw.rfind(ch)
            if idx != -1:
                apos_idx = idx
                break

        is_possessive = False
        possessive_suffix = ""
        base = raw
        if apos_idx != -1:
            suffix_letters = raw[apos_idx + 1 :]
            if suffix_letters.lower() == "s":
                is_possessive = True
                possessive_suffix = raw[apos_idx:]
                base = raw[:apos_idx]

        tokens.append(
            Token(
                text=raw,
                base=base,
                norm=base.lower(),
                start=start,
                end=end,
                is_possessive=is_possessive,
                possessive_suffix=possessive_suffix,
            )
        )
    return tokens


def normalize(s: str) -> str:
    return s.strip().lower()


def span_norm(tokens: list[Token]) -> str:
    """Normalized, space-joined form of a token span - used as the memory lookup key."""
    return " ".join(t.norm for t in tokens)


def normalize_span(text: str) -> tuple[str, str, int] | None:
    """Tokenize `text` and return (observed_form, canonical_form, token_count)
    - the shape retrieval.py/decision.py expect for a Memory row key. Returns
    None if `text` has no tokenizable words. Anything deriving a Memory row
    from free text (not by diffing an asr/corrected pair) must go through
    this rather than e.g. naive .lower()/.split(), or retrieval can silently
    never match it."""
    toks = tokenize(text)
    if not toks:
        return None
    return span_norm(toks), " ".join(t.base for t in toks), len(toks)
