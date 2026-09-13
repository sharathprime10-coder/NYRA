"""
NYRA LLM Factory — Production-grade provider management.

Architecture:
  - Gemini is PRIMARY (always available, fastest for this app).
  - Groq and OpenRouter are OPTIONAL fallbacks with circuit breakers.
  - Each provider is wrapped in a ProviderCircuit that tracks failures
    and skips dead providers automatically.

Model IDs (August 2026):
  Gemini:      gemini-3.7-flash
  Groq:        openai/gpt-oss-20b (writer), openai/gpt-oss-120b (researcher)
  OpenRouter:  meta-llama/llama-3.1-8b-instruct
"""

import logging
import time

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import Runnable
from langchain_core.runnables.fallbacks import RunnableWithFallbacks

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Circuit Breaker — skip providers that are known-dead
# ---------------------------------------------------------------------------

_TRANSIENT_COOLDOWN_S = 120  # 2 minutes
_TRANSIENT_THRESHOLD = 3  # failures before tripping


class ProviderCircuit:
    """In-memory circuit breaker for a single LLM provider."""

    def __init__(self, name: str):
        self.name = name
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.is_permanent = False  # True for model_decommissioned etc.

    def is_available(self) -> bool:
        if self.is_permanent:
            return False
        if self.failure_count >= _TRANSIENT_THRESHOLD:
            elapsed = time.time() - self.last_failure_time
            if elapsed < _TRANSIENT_COOLDOWN_S:
                return False
            # Cooldown expired — reset and allow retry
            self.failure_count = 0
        return True

    def record_success(self):
        self.failure_count = 0

    def record_failure(self, error: Exception):
        self.failure_count += 1
        self.last_failure_time = time.time()

        err_str = str(error).lower()
        # Permanent failures — never retry until server restart
        if any(
            kw in err_str
            for kw in [
                "model_decommissioned",
                "model_not_found",
                "does not exist",
                "not supported",
                "deprecated",
                "not found",
            ]
        ):
            self.is_permanent = True
            logger.error(
                "provider_permanently_disabled",
                extra={"provider": self.name, "error": str(error)},
            )
        else:
            logger.warning(
                "provider_transient_failure",
                extra={
                    "provider": self.name,
                    "failure_count": self.failure_count,
                    "error": str(error)[:200],
                },
            )


# Global circuits — one per provider
_circuits = {
    "gemini": ProviderCircuit("gemini"),
    "groq": ProviderCircuit("groq"),
    "openrouter": ProviderCircuit("openrouter"),
}


def _get_circuit(name: str) -> ProviderCircuit:
    return _circuits[name]


from langchain_core.callbacks import BaseCallbackHandler

class CircuitBreakerCallback(BaseCallbackHandler):
    """
    LangChain callback to log timing for every call and update the circuit breaker.
    """
    def __init__(self, provider_name: str, model_name: str):
        self.provider = provider_name
        self.model = model_name
        self.start_times = {}

    def on_llm_start(self, serialized, prompts, run_id, **kwargs):
        self.start_times[run_id] = time.time()

    def on_chat_model_start(self, serialized, messages, run_id, **kwargs):
        self.start_times[run_id] = time.time()

    def on_llm_end(self, response, run_id, **kwargs):
        start = self.start_times.pop(run_id, time.time())
        duration_ms = (time.time() - start) * 1000
        _get_circuit(self.provider).record_success()
        logger.info(
            "llm_call",
            extra={
                "provider": self.provider,
                "model": self.model,
                "outcome": "success",
                "duration_ms": round(duration_ms, 1),
            },
        )

    def on_llm_error(self, error, run_id, **kwargs):
        start = self.start_times.pop(run_id, time.time())
        duration_ms = (time.time() - start) * 1000
        _get_circuit(self.provider).record_failure(error)
        logger.error(
            "llm_call",
            extra={
                "provider": self.provider,
                "model": self.model,
                "outcome": "failure",
                "duration_ms": round(duration_ms, 1),
                "error": str(error)[:200],
            },
        )

# ---------------------------------------------------------------------------
# Provider builders
# ---------------------------------------------------------------------------

def _build_gemini(model: str = "gemini-3.7-flash", timeout: int = 10, **kwargs):
    """Create a Gemini LLM instance."""
    if not _get_circuit("gemini").is_available():
        return None
    llm = ChatGoogleGenerativeAI(
        model=model,
        api_key=settings.GEMINI_API_KEY,
        max_retries=1,
        request_timeout=timeout,
        callbacks=[CircuitBreakerCallback("gemini", model)],
        **kwargs,
    )
    return llm


def _build_groq(model: str = "openai/gpt-oss-20b", timeout: int = 5, **kwargs):
    """Create a Groq LLM instance (returns None if no API key or circuit open)."""
    if not settings.GROQ_API_KEY:
        return None
    if not _get_circuit("groq").is_available():
        return None
    from langchain_groq import ChatGroq

    llm = ChatGroq(
        model=model,
        api_key=settings.GROQ_API_KEY,
        max_retries=0,
        request_timeout=timeout,
        callbacks=[CircuitBreakerCallback("groq", model)],
        **kwargs,
    )
    return llm


def _build_openrouter(
    model: str = "meta-llama/llama-3.1-8b-instruct", timeout: int = 8, **kwargs
):
    """Create an OpenRouter LLM instance (returns None if no API key or circuit open)."""
    if not settings.OPENROUTER_API_KEY:
        return None
    if not _get_circuit("openrouter").is_available():
        return None
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=model,
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        timeout=timeout,
        callbacks=[CircuitBreakerCallback("openrouter", model)],
        **kwargs,
    )
    return llm


def _with_optional_fallbacks(primary, fallbacks):
    """Attach non-None fallbacks to the primary LLM."""
    valid = [fb for fb in fallbacks if fb is not None]
    if valid:
        return primary.with_fallbacks(
            fallbacks=valid, exceptions_to_handle=(Exception,)
        )
    return primary


# ---------------------------------------------------------------------------
# Public API — used by graph.py
# ---------------------------------------------------------------------------


def get_router_llm():
    """
    Ultra-fast LLM for the Supervisor routing decision.
    Uses fallback chain.
    """
    primary = _build_gemini(model="gemini-3.7-flash", timeout=10)
    groq = _build_groq(model="openai/gpt-oss-20b", timeout=10)
    # OpenRouter llama-3.1-8b-instruct does not support tools (used by with_structured_output)
    
    valid_llms = [llm for llm in [primary, groq] if llm is not None]
    if not valid_llms:
        raise ValueError("No LLM providers available for router")
    return _with_optional_fallbacks(valid_llms[0], valid_llms[1:])


def get_fast_llm():
    """Ultra-fast LLM for low-latency tasks (simple query fast-path)."""
    primary = _build_gemini(model="gemini-3.7-flash", timeout=10)
    groq = _build_groq(model="openai/gpt-oss-20b", timeout=10)
    or_llm = _build_openrouter(timeout=10)
    
    valid_llms = [llm for llm in [primary, groq, or_llm] if llm is not None]
    if not valid_llms:
        raise ValueError("No LLM providers available for fast path")
    return _with_optional_fallbacks(valid_llms[0], valid_llms[1:])


def get_frontier_llm(tools=None):
    """
    Most powerful LLM for the Researcher (complex agentic / tool-use tasks).
    Primary: Gemini 3.7 Flash
    Fallback 1: Groq gpt-oss-120b
    """
    primary = _build_gemini(model="gemini-3.7-flash", timeout=30)
    groq = _build_groq(model="openai/gpt-oss-120b", timeout=25)
    # OpenRouter llama-3.1-8b-instruct does not support tools

    valid_llms = [llm for llm in [primary, groq] if llm is not None]
    if not valid_llms:
        raise ValueError("No LLM providers available for frontier")

    head = valid_llms[0]
    tail = valid_llms[1:]
    
    if tools:
        head = head.bind_tools(tools)
        tail = [llm.bind_tools(tools) for llm in tail]

    return _with_optional_fallbacks(head, tail)


def get_writer_llm():
    """
    LLM for the Writer agent (expressive, fast drafting).
    """
    primary = _build_gemini(model="gemini-3.7-flash", timeout=30)
    groq = _build_groq(model="openai/gpt-oss-20b", timeout=25)
    or_llm = _build_openrouter(timeout=25)
    
    valid_llms = [llm for llm in [primary, groq, or_llm] if llm is not None]
    if not valid_llms:
        raise ValueError("No LLM providers available for writer")
    return _with_optional_fallbacks(valid_llms[0], valid_llms[1:])


def get_robust_llm():
    """General-purpose LLM with full fallback chain."""
    primary = _build_gemini(model="gemini-3.7-flash", timeout=30)
    groq = _build_groq(timeout=25)
    or_llm = _build_openrouter(timeout=25)
    
    valid_llms = [llm for llm in [primary, groq, or_llm] if llm is not None]
    if not valid_llms:
        raise ValueError("No LLM providers available for robust")
    return _with_optional_fallbacks(valid_llms[0], valid_llms[1:])


def get_critic_llm():
    """
    LLM for the Critic (hallucination checker).
    """
    primary = _build_gemini(model="gemini-3.7-flash", timeout=10)
    groq = _build_groq(model="openai/gpt-oss-20b", timeout=10)
    # OpenRouter llama-3.1-8b-instruct does not support tools (used by with_structured_output)
    
    valid_llms = [llm for llm in [primary, groq] if llm is not None]
    if not valid_llms:
        raise ValueError("No LLM providers available for critic")
    return _with_optional_fallbacks(valid_llms[0], valid_llms[1:])
