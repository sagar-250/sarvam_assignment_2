"""Optional LLM-backed formatter, off by default and unimplemented - a
documented extension point only. backend/formatter.py routes here if
KIVI_USE_LLM_FORMATTER=true and KIVI_LLM_API_KEY is set."""


def format_with_llm(asr_text: str) -> str:
    raise NotImplementedError(
        "LLM formatter is a documented extension point, not part of the "
        "primary review path. Set KIVI_USE_LLM_FORMATTER=false (default)."
    )
