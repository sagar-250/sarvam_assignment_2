"""Deterministic, offline, credential-free entity extraction using spaCy's
NER model - the free first pass for backend/memory_service.py::learn_from_conversations.

This is genuinely different from backend/entity_extraction.py's LLM path:
spaCy has no network dependency and needs no API key, so it works in the
primary review path with nothing but a one-time model download (see RUN.md).
The trade-off, verified directly against the actual model (not assumed):
en_core_web_sm reliably tags places and orgs ("Mumbai" -> GPE, "Google" ->
ORG), and catches a person's name when there's a supporting verb context
("Sarah called" -> PERSON), but its recall on names drops sharply without
that context, and drops to zero on names it has little training signal for -
"Rahul" is missed entirely in "Meet Rahul tomorrow...", the same sentence
shape that also happens to miss "John" (see tests/test_ner_extraction.py,
which encodes exactly this finding rather than an assumption). Invented
product names fare no better: "Meet Aaditya tomorrow to discuss the Kivi
launch in Bengaluru with Sarvam." finds "Kivi" (ORG) and "Bengaluru" (GPE)
but misses "Aaditya" and "Sarvam" entirely. So this module is deliberately
used as a first pass, not a replacement for the LLM path - see
learn_from_conversations, which merges both and is never worse than either
alone.

Loading is lazy and best-effort: if spaCy or the model isn't installed,
extract_entities_ner() returns [] rather than raising, so the rest of the
pipeline degrades to whatever the (optional) LLM pass finds, exactly the
same "never fail worse than not having this" contract backend/grouping.py
already established.
"""
from functools import lru_cache

from backend import config
from backend.entity_extraction import ExtractedEntity

# OntoNotes label -> this system's entity_type vocabulary. Only labels that
# plausibly correspond to a personal/product/place term are mapped; anything
# else (DATE, CARDINAL, EVENT, LAW, ...) is dropped, not passed through as
# "other" - a generic NER model tags plenty of spans this system has no
# business treating as a candidate memory.
SPACY_LABEL_MAP = {
    "PERSON": "person",
    "ORG": "product",   # closest fit for company/product names here
    "PRODUCT": "product",
    "GPE": "place",
    "LOC": "place",
    "FAC": "place",
}


@lru_cache(maxsize=1)
def _load_model():
    try:
        import spacy
    except ImportError:
        return None
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        # Package installed but the model itself wasn't downloaded
        # (`python -m spacy download en_core_web_sm`) - fail soft, not hard.
        return None


def ner_model_available() -> bool:
    return _load_model() is not None


def extract_entities_ner(text: str) -> list[ExtractedEntity]:
    nlp = _load_model()
    if nlp is None:
        return []

    doc = nlp(text)
    seen: set[str] = set()
    out: list[ExtractedEntity] = []
    for ent in doc.ents:
        entity_type = SPACY_LABEL_MAP.get(ent.label_)
        if entity_type is None:
            continue
        span_text = ent.text.strip()
        if not span_text or len(span_text.split()) > config.MAX_SPAN_TOKENS:
            continue
        if span_text in seen:
            continue
        seen.add(span_text)
        out.append(ExtractedEntity(entity_text=span_text, entity_type=entity_type))
    return out
