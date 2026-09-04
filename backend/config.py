import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = os.environ.get("KIVI_DB_PATH", str(BASE_DIR / "data" / "kivi_memory.db"))

# Evidence / confidence lifecycle thresholds
EVIDENCE_THRESHOLD = int(os.environ.get("KIVI_EVIDENCE_THRESHOLD", "3"))
MIN_EVIDENCE_ACTIVE = int(os.environ.get("KIVI_MIN_EVIDENCE_ACTIVE", "2"))
MIN_CONFIDENCE_ACTIVE = float(os.environ.get("KIVI_MIN_CONFIDENCE_ACTIVE", "0.6"))

# Retrieval
MAX_SPAN_TOKENS = int(os.environ.get("KIVI_MAX_SPAN_TOKENS", "3"))
CONTEXT_WINDOW = int(os.environ.get("KIVI_CONTEXT_WINDOW", "4"))

# Optional LLM formatter (off by default - see backend/formatter.py)
KIVI_LLM_API_KEY = os.environ.get("KIVI_LLM_API_KEY", "")
KIVI_USE_LLM_FORMATTER = os.environ.get("KIVI_USE_LLM_FORMATTER", "false").lower() == "true"

# Optional LLM-assisted grouping of adjacent corrections (off by default,
# see backend/grouping.py) - needs credentials too, degrades silently without them.
KIVI_LLM_GROUPING_ENABLED = os.environ.get("KIVI_LLM_GROUPING_ENABLED", "false").lower() == "true"
