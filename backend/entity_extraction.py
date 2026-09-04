"""Extracts personal/idiosyncratic named entities directly from a finished,
already-corrected conversation transcript - no raw-ASR side needed.

This is a genuinely different mechanism from backend/diff.py: diffing needs a
(wrong, right) pair to compare; a finished conversation has no "wrong" side to
diff against. Recognizing that "Aaditya" or "Kivi" are personal terms worth
remembering, from correct text alone, needs real judgment a deterministic
formatter can't provide (see backend/formatter.py's docstring) - so this
module is LLM-only, and (like backend/grouping.py) entirely optional: gated
behind real provider credentials, never touching the primary review path.

The LLM is trusted only to spot candidate spans and roughly classify them -
never to invent facts. Every candidate is verified as a literal substring of
the source text before being accepted (`_valid`); anything the model
hallucinates that isn't actually in the transcript is silently discarded.
"""
from dataclasses import dataclass

from backend import config
from backend.grouping import ALLOWED_ENTITY_TYPES
from backend.llm_client import chat_json

SYSTEM_PROMPT = "You output strict JSON only. No markdown, no commentary, no code fences."

USER_PROMPT_TEMPLATE = """Below is a finished, correctly-written conversation transcript (already \
proofread - not raw speech-to-text output).

Identify every personal or ambiguous named entity mentioned in it that a generic spell-checker or \
formatter would NOT already know how to capitalize or spell correctly on its own - specifically: \
people's names, product/brand names, and place names. Do NOT extract common dictionary words, common \
titles/roles (e.g. "manager", "doctor"), generic nouns, or ordinary words a standard grammar/\
capitalization checker already handles correctly. Only extract entities that are genuinely \
idiosyncratic, unusual, or would plausibly be misheard/misspelled by a phonetic transcription system.

For each entity, return its EXACT text as it appears verbatim in the transcript below (same spelling \
and casing) - do not paraphrase or correct it further.

Transcript:
\"\"\"
{text}
\"\"\"

Return a JSON array. Each item: {{"entity_text": "<verbatim span exactly as written above>", \
"entity_type": "person" | "product" | "place" | "other"}}. A span must be at most {max_span} words. \
If no such entities are found, return an empty array []. Output ONLY the JSON array."""


@dataclass
class ExtractedEntity:
    entity_text: str
    entity_type: str


def _valid(item: dict, source_text: str) -> bool:
    if not isinstance(item, dict):
        return False
    text = str(item.get("entity_text", "")).strip()
    etype = item.get("entity_type", "")
    if not text:
        return False
    if len(text.split()) > config.MAX_SPAN_TOKENS:
        return False
    if etype not in ALLOWED_ENTITY_TYPES:
        return False
    if text not in source_text:
        # Never trust the LLM to have named a span that isn't actually
        # present in the user's real document - reject anything it invents.
        return False
    return True


def extract_entities(conversation_text: str) -> list[ExtractedEntity]:
    """Calls the LLM once for this conversation and returns validated,
    deduplicated entities. Raises LLMCredentialsMissingError (propagated,
    uncaught) if no provider key is configured - callers decide how to
    surface that; raises whatever chat_json raises on other failures after
    its own internal retries are exhausted."""
    prompt = USER_PROMPT_TEMPLATE.format(text=conversation_text, max_span=config.MAX_SPAN_TOKENS)
    raw = chat_json(SYSTEM_PROMPT, prompt, temperature=0.2, max_tokens=1000)

    if not isinstance(raw, list):
        return []

    seen: set[str] = set()
    out: list[ExtractedEntity] = []
    for item in raw:
        if not _valid(item, conversation_text):
            continue
        text = str(item["entity_text"]).strip()
        if text in seen:
            continue
        seen.add(text)
        out.append(ExtractedEntity(entity_text=text, entity_type=item["entity_type"]))
    return out
