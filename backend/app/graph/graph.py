import sqlite3
from typing import Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

from app.core.config import settings
from app.graph.state import NYRAState
from app.tools.registry import get_all_tools
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import os

os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

# Initialize the LLMs
llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0.2)
llm_writer = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0.7) # more creative
llm_critic = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0.0) # strict

# Data Models for Routing
class Router(BaseModel):
    next_agent: Literal["researcher", "writer"] = Field(
        description="The next agent to route to. Choose 'researcher' if factual data/tools are needed. Choose 'writer' if drafting a response based on conversation context or casual chat."
    )

class CriticReview(BaseModel):
    passed: bool = Field(description="Whether the draft accurately answers the prompt without hallucinations.")
    feedback: str = Field(description="Feedback on why it failed, or empty if it passed.")

def supervisor_node(state: NYRAState, config=None):
    """Orchestrator that routes to the appropriate specialist agent."""
    messages = state["messages"]
    system_msg = SystemMessage(
        content="You are the NYRA Orchestrator. Analyze the conversation. "
                "If the user asks a factual question, needs calculations, or document retrieval, route to 'researcher'. "
                "If the user asks a conversational question or asks to draft text based on history, route to 'writer'."
    )
    
    # Use structured output for routing
    router_llm = llm.with_structured_output(Router)
    decision = router_llm.invoke([system_msg] + messages, config=config)
    
    # We don't add the supervisor's thought to the message history, just route it
    return {"sender": "supervisor", "next_node": decision.next_agent}

def researcher_node(state: NYRAState, config=None):
    """Agent specifically bound to tools to gather information."""
    messages = state["messages"]
    system_msg = SystemMessage(
        content="You are the NYRA Researcher. Your ONLY job is to use tools to gather facts, search the web, or read files. "
                "Do NOT write a conversational response to the user. Just gather the data."
    )
    
    # Late bind tools to ensure MCP is loaded
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    response = llm_with_tools.invoke([system_msg] + messages, config=config)
    return {"messages": [response], "sender": "researcher"}

def writer_node(state: NYRAState, config=None):
    """Drafts the final response to the user."""
    messages = state["messages"]
    system_msg = SystemMessage(
        content="You are the NYRA Writer. Your job is to draft a helpful, professional, and accurate response to the user. "
                "Use the conversation history and any data provided by the researcher. "
                "Output your response clearly in markdown."
    )
    
    response = llm_writer.invoke([system_msg] + messages, config=config)
    return {"draft": response.content, "sender": "writer"}

def critic_node(state: NYRAState, config=None):
    """Evaluates the writer's draft for quality and accuracy."""
    draft = state.get("draft", "")
    messages = state["messages"]
    
    system_msg = SystemMessage(
        content=f"You are the NYRA Critic. Evaluate the following draft response:\n\n{draft}\n\n"
                f"Does this draft directly and accurately answer the user's latest prompt based on the context? "
                f"Ensure there are no hallucinations."
    )
    
    evaluator_llm = llm_critic.with_structured_output(CriticReview)
    review = evaluator_llm.invoke([system_msg] + messages, config=config)
    
    if review.passed:
        # If passed, we finally append the draft to the message history as an AIMessage
        return {"messages": [AIMessage(content=draft)], "sender": "critic", "next_node": "FINISH"}
    else:
        # If failed, add the feedback to the context for the writer
        feedback_msg = HumanMessage(content=f"CRITIC FEEDBACK: The draft was rejected. Reason: {review.feedback}. Please rewrite it.")
        return {"messages": [feedback_msg], "sender": "critic", "next_node": "writer"}

# Create a lazy loader class that inherits from ToolNode but defers tool resolution
class LazyToolNode:
    def __init__(self, get_tools_func):
        self.get_tools_func = get_tools_func
        self._node = None
        
    def __call__(self, state, config=None):
        if not self._node:
            self._node = ToolNode(self.get_tools_func())
        return self._node(state, config=config)

tool_node = LazyToolNode(get_all_tools)

# Routing logic
def route_from_supervisor(state: NYRAState):
    return state.get("next_node", "writer")

def route_from_researcher(state: NYRAState):
    messages = state["messages"]
    last_message = messages[-1]
    # If the researcher invoked a tool, go to tools
    if last_message.tool_calls:
        return "tools"
    # Otherwise, it finished gathering info, go to writer
    return "writer"

def route_from_critic(state: NYRAState):
    return state.get("next_node", "FINISH")

# Build the Multi-Agent Graph
graph = StateGraph(NYRAState)

graph.add_node("supervisor", supervisor_node)
graph.add_node("researcher", researcher_node)
graph.add_node("writer", writer_node)
graph.add_node("critic", critic_node)
graph.add_node("tools", tool_node)

# Connect edges
graph.add_edge(START, "supervisor")

graph.add_conditional_edges("supervisor", route_from_supervisor, {
    "researcher": "researcher",
    "writer": "writer"
})

graph.add_conditional_edges("researcher", route_from_researcher, {
    "tools": "tools",
    "writer": "writer"
})
graph.add_edge("tools", "researcher")

graph.add_edge("writer", "critic")

graph.add_conditional_edges("critic", route_from_critic, {
    "writer": "writer",
    "FINISH": END
})

# Checkpointer
conn = sqlite3.connect("nyra_checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

nyra_graph = graph.compile(checkpointer=checkpointer)
