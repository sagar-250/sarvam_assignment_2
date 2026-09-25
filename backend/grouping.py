"""Optional passes that merge adjacent word-level corrections into one
multi-word entity when they belong together (e.g. "new" + "yolk sity" ->
"New York City"), while leaving genuinely unrelated adjacent corrections
separate (e.g. "sarvam" + "kiwi"). Two independent backends, both off by
default and both no-ops on the primary zero-credential path:

- ONNX NER (config.KIVI_NER_GROUPING_ENABLED): free, no credentials, tried
  first. Only trusted for person-name merges - see
  onnx_ner.should_merge_combined_span for why product/place merges from this
  signal are deliberately never auto-applied.
- LLM (config.KIVI_LLM_GROUPING_ENABLED): the fallback for everything NER
  doesn't confidently resolve - actual semantic judgment for the cases that
  need it (is this one brand or two), not just span-boundary detection.
"""
from backend import config
from backend.diff import ObservationPair
from backend.llm_client import LLMCredentialsMissingError, chat_json

ALLOWED_ENTITY_TYPES = {"person", "product", "place", "other"}

SYSTEM_PROMPT = "You output strict JSON only. No markdown, no commentary, no code fences."

USER_PROMPT_TEMPLATE = """Below is a corrected sentence, along with two adjacent word-level \
corrections that were learned separately from it (a word-level diff can't tell whether adjacent \
corrections belong together).

Decide: are these actually ONE single multi-word named entity (e.g. "New York City" is one place \
name, even though "New" and "York City" might have been corrected as separate words) - or TWO \
unrelated corrections that just happen to sit next to each other (e.g. "Sarvam" and "Kivi" are two \
different product/brand names in the same sentence; correcting both does not make them one entity)?

Corrected sentence: "{corrected_text}"

Correction 1: "{a_observed}" -> "{a_canonical}"
Correction 2: "{b_observed}" -> "{b_canonical}"
Adjacent as written: "{a_canonical} {b_canonical}"

Return ONLY JSON: {{"merge": true or false, "entity_type": "person" | "product" | "place" | "other"}}
entity_type is only meaningful when merge is true - it's the type of the resulting combined entity."""


def _ask_llm_should_merge(a: ObservationPair, b: ObservationPair, corrected_text: str) -> tuple[bool, str]:
    prompt = USER_PROMPT_TEMPLATE.format(
        corrected_text=corrected_text,
        a_observed=a.observed_form, a_canonical=a.canonical_form,
        b_observed=b.observed_form, b_canonical=b.canonical_form,
    )
    raw = chat_json(SYSTEM_PROMPT, prompt, temperature=0.0, max_tokens=100)
    if not isinstance(raw, dict):
        return False, "other"
    merge = bool(raw.get("merge", False))
    entity_type = raw.get("entity_type", "other")
    if entity_type not in ALLOWED_ENTITY_TYPES:
        entity_type = "other"
    return merge, entity_type


def _try_ner_merge(a: ObservationPair, b: ObservationPair, corrected_text: str) -> tuple[bool, str, bool]:
    """Returns (should_merge, entity_type, decided). decided=True means NER
    had an opinion worth trusting (a person-name merge, or a covering span of
    a type we don't auto-merge - either way, no need to also ask the LLM);
    decided=False means NER found nothing here and the caller should fall
    through to the LLM path unchanged."""
    from backend.onnx_ner import onnx_ner_available, should_merge_combined_span

    if not onnx_ner_available():
        return False, "other", False

    combined_text = f"{a.canonical_form} {b.canonical_form}"
    combined_start = corrected_text.find(combined_text)
    if combined_start == -1:
        return False, "other", False

    should_merge, entity_type = should_merge_combined_span(
        combined_start, combined_start + len(combined_text), corrected_text
    )
    if entity_type is None:
        return False, "other", False  # no covering entity at all - let the LLM path decide
    return should_merge, (entity_type or "other"), True


def maybe_group_adjacent_pairs(
    pairs: list[ObservationPair], corrected_text: str
) -> tuple[list[ObservationPair], bool]:
    """Try to merge each pair of adjacent-in-text corrections that belong
    together, NER first (free, person-names only - see module docstring),
    then the LLM (if enabled) for anything NER didn't resolve. Returns
    (possibly-merged pairs, whether an LLM call was attempted). Any LLM
    failure - flag off, no credentials, malformed output, network error -
    falls back to `pairs` unchanged for that pair."""
    if (not config.KIVI_NER_GROUPING_ENABLED and not config.KIVI_LLM_GROUPING_ENABLED) or len(pairs) < 2:
        return pairs, False

    merged: list[ObservationPair] = []
    attempted = False
    i = 0
    while i < len(pairs):
        if i + 1 < len(pairs) and f"{pairs[i].canonical_form} {pairs[i + 1].canonical_form}" in corrected_text:
            a, b = pairs[i], pairs[i + 1]
            combined_token_count = a.token_count + b.token_count
            if combined_token_count <= config.MAX_SPAN_TOKENS:
                should_merge, entity_type, decided = False, "other", False

                if config.KIVI_NER_GROUPING_ENABLED:
                    should_merge, entity_type, decided = _try_ner_merge(a, b, corrected_text)

                if not decided and config.KIVI_LLM_GROUPING_ENABLED:
                    try:
                        attempted = True
                        should_merge, entity_type = _ask_llm_should_merge(a, b, corrected_text)
                    except LLMCredentialsMissingError:
                        return pairs, False
                    except Exception:  # noqa: BLE001 - never let a grouping failure break learning
                        should_merge, entity_type = False, "other"

                if should_merge:
                    merged.append(
                        ObservationPair(
                            observed_form=f"{a.observed_form} {b.observed_form}",
                            canonical_form=f"{a.canonical_form} {b.canonical_form}",
                            token_count=combined_token_count,
                            entity_type=entity_type,
                        )
                    )
                    i += 2
                    continue
        merged.append(pairs[i])
        i += 1

    return merged, attempted
