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

# Below this many memory rows, retrieval loads the whole table once and
# matches in Python; above it, exact match uses batched indexed SQL queries
# and fuzzy match uses a cached SymSpell index. Indexing/caching overhead
# only pays off once the table is big - see eval/benchmark_retrieval.py for
# the measured crossover point this default is based on.
RETRIEVAL_SMALL_TABLE_THRESHOLD = int(os.environ.get("KIVI_RETRIEVAL_SMALL_TABLE_THRESHOLD", "2000"))

# Optional LLM formatter (off by default - see backend/formatter.py)
KIVI_LLM_API_KEY = os.environ.get("KIVI_LLM_API_KEY", "")
KIVI_USE_LLM_FORMATTER = os.environ.get("KIVI_USE_LLM_FORMATTER", "false").lower() == "true"

# Optional LLM-assisted grouping of adjacent corrections (off by default,
# see backend/grouping.py) - needs credentials too, degrades silently without them.
KIVI_LLM_GROUPING_ENABLED = os.environ.get("KIVI_LLM_GROUPING_ENABLED", "false").lower() == "true"

# Optional ONNX-quantized NER backend (dslim/bert-base-NER, int8 via
# onnxruntime - see backend/onnx_ner.py). Off by default: "spacy" keeps the
# existing free/offline behavior unchanged everywhere. Switching to "onnx"
# needs `pip install optimum[onnxruntime] onnxruntime` and a locally
# exported+quantized model directory - see README for the export commands.
# Missing dependency or missing export dir both fail soft to the prior
# behavior (cue-word heuristic in diff.py, spaCy in ner_extraction.py).
KIVI_NER_BACKEND = os.environ.get("KIVI_NER_BACKEND", "spacy")  # "spacy" | "onnx"
KIVI_ONNX_NER_DIR = os.environ.get("KIVI_ONNX_NER_DIR", str(BASE_DIR / "models" / "dslim-onnx"))

# Optional: use the ONNX NER backend as the ambiguous-word gate in
# decision.py, instead of the hand-curated COMMON_WORD_CUES cue-word list.
# Off by default - one extra model call per /run request (not per candidate,
# see decision.py) only when there's an ambiguous-word candidate to check.
KIVI_NER_AMBIGUOUS_GATE_ENABLED = os.environ.get("KIVI_NER_AMBIGUOUS_GATE_ENABLED", "false").lower() == "true"
