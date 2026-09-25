"""ONNX-quantized dslim/bert-base-NER backend - an optional, faster
alternative to the spaCy backend in ner_extraction.py. Off by default
(config.KIVI_NER_BACKEND="spacy"); opt in once a quantized model has been
exported locally (see README for the export+quantize commands - this needs
`pip install optimum[onnxruntime] onnxruntime`, neither a hard dependency of
the primary path). Loading is lazy and best-effort, same contract as
ner_extraction.py: a missing dependency or a missing/broken export directory
returns "unavailable" rather than raising, so callers fall back cleanly.

Two entry points, for the two call sites that use it:
- extract_entities_onnx(): same shape as ner_extraction.extract_entities_ner
  (verbatim ExtractedEntity spans) - a drop-in alternative source for the
  bulk-conversation import path (Mode 2), if ever wired in there too.
- extract_entity_spans(): character-offset (start, end, entity_type) spans
  for containment checks - what diff.py's entity-type inference and
  decision.py's ambiguous-word gate actually use, since both need to ask
  "is this specific span covered by an entity" rather than "list every span."
"""
from functools import lru_cache

from backend import config
from backend.entity_extraction import ExtractedEntity

# CoNLL-2003 label set (what dslim/bert-base-NER was trained on) -> this
# system's entity_type vocabulary. Same "closest fit" mapping approach as
# ner_extraction.SPACY_LABEL_MAP. MISC is deliberately dropped - too generic
# to trust as a personal/product/place term.
CONLL_LABEL_MAP = {
    "PER": "person",
    "ORG": "product",
    "LOC": "place",
}


@lru_cache(maxsize=1)
def _load_pipeline():
    try:
        from optimum.onnxruntime import ORTModelForTokenClassification
        from transformers import AutoTokenizer, pipeline
    except ImportError:
        return None
    try:
        model = ORTModelForTokenClassification.from_pretrained(
            config.KIVI_ONNX_NER_DIR, file_name="model_quantized.onnx"
        )
        tokenizer = AutoTokenizer.from_pretrained(config.KIVI_ONNX_NER_DIR)
        return pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
    except Exception:  # noqa: BLE001 - missing/broken export dir, fail soft like ner_extraction does
        return None


def onnx_ner_available() -> bool:
    return _load_pipeline() is not None


@lru_cache(maxsize=64)
def _run_ner_cached(text: str) -> tuple:
    """Caches the raw pipeline call per distinct text - diff.py calls
    entity-type inference once per observation *pair*, so a sentence with
    multiple corrections would otherwise re-run the model on the identical
    sentence multiple times in the same request."""
    ner = _load_pipeline()
    if ner is None:
        return ()
    return tuple(ner(text))


def extract_entities_onnx(text: str) -> list[ExtractedEntity]:
    """Same contract as ner_extraction.extract_entities_ner: verbatim spans,
    deduplicated, capped at MAX_SPAN_TOKENS words."""
    seen: set[str] = set()
    out: list[ExtractedEntity] = []
    for r in _run_ner_cached(text):
        entity_type = CONLL_LABEL_MAP.get(r["entity_group"])
        if entity_type is None:
            continue
        span_text = r["word"].strip()
        if not span_text or len(span_text.split()) > config.MAX_SPAN_TOKENS:
            continue
        if span_text in seen:
            continue
        seen.add(span_text)
        out.append(ExtractedEntity(entity_text=span_text, entity_type=entity_type))
    return out


def extract_entity_spans(text: str) -> list[tuple[int, int, str]]:
    """(start_char, end_char, entity_type) tuples for containment checks -
    lets a caller ask "is token span [a, b) covered by a matching-type
    entity" without a separate model call per candidate span."""
    spans = []
    for r in _run_ner_cached(text):
        entity_type = CONLL_LABEL_MAP.get(r["entity_group"])
        if entity_type is None:
            continue
        spans.append((r["start"], r["end"], entity_type))
    return spans


def should_merge_combined_span(combined_start: int, combined_end: int, text: str) -> tuple[bool, str | None]:
    """Is [combined_start, combined_end) - the text of two adjacent diff
    pairs joined together - covered by a SINGLE NER entity span? Used by
    grouping.py to decide whether two adjacent corrections are one
    multi-word entity.

    Only ever returns should_merge=True for entity_type == "person": full
    name + surname merging was verified reliable (10/10 across varied
    sentence patterns), but brand/product-pair merging was verified
    UNRELIABLE - the same model merged "Sarvam Kivi" into one entity (wrong
    for this system) while splitting the real compound name "Google Pixel"
    into two, inconsistently, in the same test run. So a covering ORG/
    PRODUCT/PLACE span is reported back (the caller may still want to know
    NER saw *something* here) but never auto-trusted to merge - that
    decision stays with the LLM path (if enabled) or stays unmerged, same as
    before this backend existed."""
    for start, end, entity_type in extract_entity_spans(text):
        if start <= combined_start and combined_end <= end:
            return entity_type == "person", entity_type
    return False, None
