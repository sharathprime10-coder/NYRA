import threading
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

# Simple thread-safe in-memory store for session token usage
# In production, this should be stored in Redis or PostgreSQL
_session_usage: dict[str, dict[str, int]] = {}
_lock = threading.Lock()


class TokenTrackerCallback(BaseCallbackHandler):
    """Callback handler to track token usage per node and session."""

    def __init__(self, session_id: str, node_name: str):
        self.session_id = session_id
        self.node_name = node_name

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        """Collect token usage after LLM call finishes."""
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            total_tokens = usage.get("total_tokens", 0)

            with _lock:
                if self.session_id not in _session_usage:
                    _session_usage[self.session_id] = {"total_tokens": 0, "nodes": {}}

                session_data = _session_usage[self.session_id]
                session_data["total_tokens"] += total_tokens

                if self.node_name not in session_data["nodes"]:
                    session_data["nodes"][self.node_name] = 0
                session_data["nodes"][self.node_name] += total_tokens


def get_session_usage(session_id: str) -> dict[str, Any]:
    with _lock:
        return _session_usage.get(session_id, {"total_tokens": 0, "nodes": {}})


def get_all_usage() -> dict[str, Any]:
    with _lock:
        return dict(_session_usage)
