from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class NYRAState(TypedDict):
    """The state schema for the NYRA LangGraph."""

    # The list of messages in the conversation
    messages: Annotated[list[BaseMessage], add_messages]

    # Metadata for the current execution
    user_id: int | None
    session_id: int | None
    document_id: str | None

    # Multi-Agent State
    sender: str | None
    draft: str | None
    next_node: str | None
    error_retries: int | None
    critic_attempts: int | None
    tool_invoked: bool | None
    routing_path: str | None

    # RAG Retrieval Safeguards
    research_iterations: int | None
    retrieval_failed: bool | None
