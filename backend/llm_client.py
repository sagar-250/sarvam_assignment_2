"""Thin, optional LLM client - used by dev/eval tooling in tools/ and eval/,
and by opt-in backend features (backend/grouping.py) that are gated behind an
explicit config flag AND real credentials. Never called on the primary,
credential-free review path described in RUN.md.

Provider defaults to Mistral (KIVI_LLM_PROVIDER=mistral), since it proved far
faster and more reliable on this account than NVIDIA NIM (which was tried
first - see README "Optional: LLM-assisted eval scale-out" for the full
comparison). Set KIVI_LLM_PROVIDER=nvidia to switch back.

Reads MISTRAL_KEY / NVIDIA_KEY from the environment, falling back to a `.env`
one level above this repo for local dev convenience - a reviewer's clone
needs the real environment variables (documented in .env.example).
"""
import json
import os
import re
import time
from collections import deque
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PARENT_ENV = REPO_ROOT.parent / ".env"

PROVIDER = os.environ.get("KIVI_LLM_PROVIDER", "mistral")

PROVIDER_CONFIG = {
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "key_name": "MISTRAL_KEY",
        "default_model": "open-mistral-nemo",
        "max_req_per_window": 100,  # observed quota is 188/min; stay well under it
        "read_timeout": 30.0,
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "key_name": "NVIDIA_KEY",
        "default_model": "nvidia/nemotron-3-ultra-550b-a55b",
        "max_req_per_window": 35,  # safety margin under NVIDIA's 40/min limit
        "read_timeout": 45.0,
    },
}

_cfg = PROVIDER_CONFIG[PROVIDER]
BASE_URL = _cfg["base_url"]
DEFAULT_MODEL = os.environ.get("KIVI_LLM_MODEL", _cfg["default_model"])
WINDOW_SECONDS = 60


class LLMCredentialsMissingError(RuntimeError):
    """Raised when the configured provider's API key isn't available. Callers
    that want to treat "no LLM configured" as a normal, expected condition
    (rather than a transient failure worth retrying) should catch this
    specifically - chat_json() re-raises it immediately, without retrying."""


def _load_key() -> str:
    key_name = _cfg["key_name"]
    key = os.environ.get(key_name)
    if key:
        return key
    if PARENT_ENV.exists():
        for line in PARENT_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{key_name}="):
                return line.split("=", 1)[1].strip()
    raise LLMCredentialsMissingError(
        f"{key_name} not found in environment or in {PARENT_ENV}. "
        "This is only needed for optional, explicitly-enabled LLM features."
    )


class RateLimiter:
    def __init__(self, max_calls: int, window: float = WINDOW_SECONDS):
        self.max_calls = max_calls
        self.window = window
        self._timestamps: deque[float] = deque()

    def wait(self) -> None:
        now = time.monotonic()
        while self._timestamps and now - self._timestamps[0] > self.window:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.max_calls:
            sleep_for = self.window - (now - self._timestamps[0]) + 0.1
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._timestamps.append(time.monotonic())


_rate_limiter = RateLimiter(max_calls=_cfg["max_req_per_window"])


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    return m.group(1) if m else text


def chat_json(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_retries: int = 3,
    temperature: float = 0.9,
    max_tokens: int = 2000,
) -> dict | list:
    """Calls the LLM and parses the response as JSON, with rate limiting,
    code-fence stripping, and retries on malformed output or transient errors.

    Uses httpx directly against the provider's OpenAI-compatible REST
    endpoint - no extra SDK dependency needed (httpx is already a project
    dependency).

    Missing credentials (LLMCredentialsMissingError) are NOT retried - that's
    a configuration state, not a transient failure, so it fails fast.
    """
    import httpx

    model = model or DEFAULT_MODEL
    url = f"{BASE_URL}/chat/completions"

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            headers = {
                "Authorization": f"Bearer {_load_key()}",
                "Content-Type": "application/json",
            }
        except LLMCredentialsMissingError:
            raise

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        timeout = httpx.Timeout(connect=10.0, read=_cfg["read_timeout"], write=10.0, pool=10.0)

        _rate_limiter.wait()
        t0 = time.monotonic()
        print(f"  [llm_client:{PROVIDER}] calling {model} (attempt {attempt}/{max_retries})...", flush=True)
        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            elapsed = time.monotonic() - t0
            print(f"  [llm_client:{PROVIDER}] done in {elapsed:.1f}s", flush=True)
            return json.loads(_strip_code_fence(content))
        except Exception as e:  # noqa: BLE001 - broad on purpose, this is best-effort tooling
            last_error = e
            elapsed = time.monotonic() - t0
            print(f"  [llm_client:{PROVIDER}] attempt {attempt}/{max_retries} failed after {elapsed:.1f}s: {e}", flush=True)
            time.sleep(1.5 * attempt)

    raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_error}")
