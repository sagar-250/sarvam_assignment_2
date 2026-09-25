"""Optional passes that merge adjacent word-level corrections into one
multi-word entity when they belong together (e.g. "new" + "yolk sity" ->
"New York City"), while leaving genuinely unrelated adjacent corrections
separate (e.g. "sarvam" + "kiwi"). Two independent backends, both off by
default and both no-ops on the primary zero-credential path:

- ONNX NER (config.KIVI_NER_GROUPING_ENABLED): free, no credentials, tried
  first on the corrected text. Merges the longest run of adjacent
  corrections covered by one person/place entity ("salt" + "lake" + "city"
  -> one memory) - see onnx_ner.MERGEABLE_ENTITY_TYPES for why product
  merges from this signal are deliberately never auto-applied.
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


def _combine(run: list[ObservationPair], entity_type: str) -> ObservationPair:
    return ObservationPair(
        observed_form=" ".join(p.observed_form for p in run),
        canonical_form=" ".join(p.canonical_form for p in run),
        token_count=sum(p.token_count for p in run),
        entity_type=entity_type,
    )


def _ner_merge_run(pairs: list[ObservationPair], i: int, corrected_text: str) -> tuple[int, str] | None:
    """Longest run pairs[i..j] (j > i) that is written adjacently in
    corrected_text, fits in MAX_SPAN_TOKENS, and sits inside one mergeable
    NER entity. Returns (j, entity_type), or None when NER merges nothing
    here - the caller then falls through to the LLM path unchanged."""
    from backend.onnx_ner import onnx_ner_available, should_merge_combined_span

    if not onnx_ner_available():
        return None

    best = None
    combined_text = pairs[i].canonical_form
    token_count = pairs[i].token_count
    for j in range(i + 1, len(pairs)):
        combined_text = f"{combined_text} {pairs[j].canonical_form}"
        token_count += pairs[j].token_count
        if token_count > config.MAX_SPAN_TOKENS:
            break
        start = corrected_text.find(combined_text)
        if start == -1:
            break
        should_merge, entity_type = should_merge_combined_span(start, start + len(combined_text), corrected_text)
        if not should_merge:
            break  # a longer run can't be covered if this prefix isn't
        best = (j, entity_type)
    return best


def maybe_group_adjacent_pairs(
    pairs: list[ObservationPair], corrected_text: str
) -> tuple[list[ObservationPair], bool]:
    """Merge adjacent-in-text corrections that belong together: NER first
    (free, person/place runs - see module docstring), then the LLM (if
    enabled) pairwise for anything NER didn't merge. Returns (possibly-merged
    pairs, whether an LLM call was attempted). Any LLM failure - flag off, no
    credentials, malformed output, network error - leaves that pair
    unmerged."""
    if (not config.KIVI_NER_GROUPING_ENABLED and not config.KIVI_LLM_GROUPING_ENABLED) or len(pairs) < 2:
        return pairs, False

    merged: list[ObservationPair] = []
    attempted = False
    llm_enabled = config.KIVI_LLM_GROUPING_ENABLED
    i = 0
    while i < len(pairs):
        if config.KIVI_NER_GROUPING_ENABLED:
            run = _ner_merge_run(pairs, i, corrected_text)
            if run is not None:
                j, entity_type = run
                merged.append(_combine(pairs[i : j + 1], entity_type))
                i = j + 1
                continue

        if (
            llm_enabled
            and i + 1 < len(pairs)
            and f"{pairs[i].canonical_form} {pairs[i + 1].canonical_form}" in corrected_text
            and pairs[i].token_count + pairs[i + 1].token_count <= config.MAX_SPAN_TOKENS
        ):
            a, b = pairs[i], pairs[i + 1]
            try:
                should_merge, entity_type = _ask_llm_should_merge(a, b, corrected_text)
                attempted = True
            except LLMCredentialsMissingError:
                llm_enabled = False  # no key - stop asking, keep any NER merges
                should_merge, entity_type = False, "other"
            except Exception:  # noqa: BLE001 - never let a grouping failure break learning
                attempted = True
                should_merge, entity_type = False, "other"

            if should_merge:
                merged.append(_combine([a, b], entity_type))
                i += 2
                continue

        merged.append(pairs[i])
        i += 1

    return merged, attempted
