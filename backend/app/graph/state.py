from typing import Annotated, TypedDict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class NYRAState(TypedDict):
    """The state schema for the NYRA LangGraph."""
    # The list of messages in the conversation
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Metadata for the current execution
    user_id: Optional[int]
    session_id: Optional[int]
    
    # Multi-Agent State
    sender: Optional[str]
    draft: Optional[str]
