"""Deterministic, offline, credential-free entity extraction via spaCy - the
free first pass for memory_service.learn_from_conversations, refined (not
replaced) by the optional LLM pass in entity_extraction.py. Recall is
genuinely imperfect on idiosyncratic names (verified in
tests/test_ner_extraction.py; see README for the measured example). Loading
is lazy and best-effort: if spaCy or the model isn't installed,
extract_entities_ner() returns [] rather than raising."""
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
