"""Optional, off-by-default LLM-assisted grouping for the fragmentation
limitation documented in README ("Sentence-initial re-casing never gets
learned, but mid-sentence re-casing does"): word-level diffing (backend/diff.py)
can't tell "these two adjacent corrections are one multi-word entity" (e.g.
teaching "new yolk sity" -> "New York City" learns "new" -> "New" and
"yolk sity" -> "York City" as two separate memories) from "these two adjacent
corrections are unrelated" (e.g. the brief's own flagship example, where
"sarvam" -> "Sarvam" sits right next to "kiwi" -> "Kivi" and must stay
separate). A real NER/LLM judgment call is exactly what's needed to
disambiguate the two - and exactly what backend/formatter.py's docstring
already says is out of scope for the deterministic path.

Gated behind config.KIVI_LLM_GROUPING_ENABLED (default False) AND real LLM
credentials. When either is unavailable, this is a no-op: the existing
deterministic (possibly-fragmented, but still individually-correct) pairs
pass through completely unchanged, so the primary zero-credential review
path and eval/tests are never affected by this module.
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


def maybe_group_adjacent_pairs(
    pairs: list[ObservationPair], corrected_text: str
) -> tuple[list[ObservationPair], bool]:
    """If grouping is enabled and credentials are available, ask the LLM
    about each pair of adjacent-in-text corrections and merge the ones it
    says form one entity. Returns (possibly-merged pairs, whether any LLM
    call was actually attempted) - the caller uses the flag purely for
    reporting/logging, never for control flow.

    Any failure (flag off, no credentials, malformed LLM output, network
    error) falls back to returning `pairs` completely unchanged - this must
    never be able to make behavior worse than not grouping at all."""
    if not config.KIVI_LLM_GROUPING_ENABLED or len(pairs) < 2:
        return pairs, False

    merged: list[ObservationPair] = []
    attempted = False
    i = 0
    while i < len(pairs):
        if i + 1 < len(pairs) and f"{pairs[i].canonical_form} {pairs[i + 1].canonical_form}" in corrected_text:
            a, b = pairs[i], pairs[i + 1]
            combined_token_count = a.token_count + b.token_count
            if combined_token_count <= config.MAX_SPAN_TOKENS:
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
