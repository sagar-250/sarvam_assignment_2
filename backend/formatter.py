"""ASR -> formatted text.

Deliberately minimal and deterministic: sentence-initial capitalization and
terminal punctuation only. It does NOT attempt general proper-noun detection
(e.g. guessing that "aditya" should be capitalized) - that would require real
NER/LLM judgement, which is out of scope for this assignment. That gap is
exactly what the memory layer exists to fill for the terms that matter to
this specific user. See README "Design decisions" for the full rationale.

An LLM-backed formatter can be swapped in later (see llm_formatter placeholder
below) but is OFF by default so the primary review path needs no API key.
"""
import re

from backend import config

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_TERMINAL_PUNCT_RE = re.compile(r"[.!?]\s*$")


def _capitalize_first_alpha(sentence: str) -> str:
    for i, ch in enumerate(sentence):
        if ch.isalpha():
            return sentence[:i] + ch.upper() + sentence[i + 1 :]
    return sentence


def format_text(asr_text: str) -> str:
    text = asr_text.strip()
    if not text:
        return text

    sentences = _SENTENCE_SPLIT_RE.split(text)
    sentences = [_capitalize_first_alpha(s.strip()) for s in sentences if s.strip()]
    formatted = " ".join(sentences)

    if not _TERMINAL_PUNCT_RE.search(formatted):
        formatted += "."

    return formatted


def format(asr_text: str) -> str:
    if config.KIVI_USE_LLM_FORMATTER and config.KIVI_LLM_API_KEY:
        from backend.llm_formatter import format_with_llm

        return format_with_llm(asr_text)
    return format_text(asr_text)
