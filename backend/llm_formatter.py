"""Optional LLM-backed formatter - OFF by default.

Not required for the primary (local, no-credentials) review path. Documented
here as an extension point only: if KIVI_USE_LLM_FORMATTER=true and
KIVI_LLM_API_KEY is set, backend/formatter.py routes through this module
instead of the deterministic rule-based formatter. Left unimplemented in this
submission - the rule-based formatter is the reviewed default (see README,
"Design decisions: rule-based vs LLM formatting").
"""


def format_with_llm(asr_text: str) -> str:
    raise NotImplementedError(
        "LLM formatter is a documented extension point, not part of the "
        "primary review path. Set KIVI_USE_LLM_FORMATTER=false (default)."
    )
