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
from app.core.llm_factory import get_robust_llm, get_writer_llm, get_critic_llm, get_frontier_llm, get_fast_llm
import os

os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY
if settings.GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY

# Initialize the LLMs
llm = get_frontier_llm() # Supervisor & Researcher (complex routing and tool use)
llm_writer = get_writer_llm() # Writer (expressive, fast drafting)
llm_critic = get_critic_llm() # Critic (deep reasoning to catch hallucinations)

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
    thinking_level = config.get("configurable", {}).get("thinking_level", "medium") if config else "medium"
    
    # If thinking level is low, bypass reasoning and immediately draft
    if thinking_level == "low":
        return {"sender": "supervisor", "next_node": "writer"}
        
    messages = state["messages"]
    system_msg = SystemMessage(
        content="You are the NYRA Orchestrator. Analyze the conversation. "
                "If the user asks a factual question, needs calculations, or document retrieval, route to 'researcher'. "
                "If the user asks a conversational question or asks to draft text based on history, route to 'writer'."
    )
    
    # Use structured output for routing
    router_llm = llm.with_structured_output(Router)
    try:
        decision = router_llm.invoke([system_msg] + messages, config=config)
        next_agent = decision.next_agent
    except Exception as e:
        import logging
        logging.error(f"Supervisor LLM failed: {e}")
        next_agent = "writer" # Fallback to writer if routing fails
    
    # We don't add the supervisor's thought to the message history, just route it
    return {"sender": "supervisor", "next_node": next_agent}

def researcher_node(state: NYRAState, config=None):
    """Agent specifically bound to tools to gather information."""
    messages = state["messages"]
    system_msg = SystemMessage(
        content="You are the NYRA Researcher. Your ONLY job is to use tools to gather facts, search the web, or read files. "
                "Do NOT write a conversational response to the user. Just gather the data.\n"
                "CRITICAL INSTRUCTION: You MUST use native JSON tool calling capabilities provided by the API. "
                "NEVER output XML tags like `<function>` or `<tool>`. Your tool calls must be valid JSON."
    )
    
    # Late bind tools to ensure MCP is loaded
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    try:
        response = llm_with_tools.invoke([system_msg] + messages, config=config)
        return {"messages": [response], "sender": "researcher", "error_retries": 0}
    except Exception as e:
        import logging
        logging.error(f"Researcher LLM failed: {e}")
        
        # Auto-healing loop
        retries = state.get("error_retries", 0) or 0
        if retries < 3:
            error_msg = HumanMessage(content=f"SYSTEM ERROR: Your previous tool call failed with the following error: {str(e)}. "
                                             f"Please analyze the error and try again. Ensure you are using strict JSON formatting for your tool calls without any markdown tags.")
            return {"messages": [error_msg], "sender": "researcher", "error_retries": retries + 1, "next_node": "self_correct"}
        else:
            return {"messages": [AIMessage(content=f"Error gathering data after multiple attempts: {str(e)}")], "sender": "researcher", "next_node": "writer"}

def writer_node(state: NYRAState, config=None):
    """Drafts the final response to the user."""
    thinking_level = config.get("configurable", {}).get("thinking_level", "medium") if config else "medium"
    messages = state["messages"]
    
    content = "You are the NYRA Writer. Your job is to draft a helpful, professional, and accurate response to the user. "
    content += "Use the conversation history and any data provided by the researcher. Output your response clearly in markdown."
    
    if thinking_level == "high":
        content += "\nCRITICAL INSTRUCTION: You MUST use deep Chain-of-Thought reasoning. First, analyze all constraints and facts in a `<thought>` block. Then, write your response."
        
    system_msg = SystemMessage(content=content)
    
    # Select the model based on thinking level
    current_writer_llm = get_fast_llm() if thinking_level == "low" else llm_writer
    
    try:
        response = current_writer_llm.invoke([system_msg] + messages, config=config)
        return {"messages": [AIMessage(content=response.content)], "draft": response.content, "sender": "writer"}
    except Exception as e:
        import logging
        error_text = f"I'm sorry, but I encountered an internal error: {str(e)}"
        return {"messages": [AIMessage(content=error_text)], "draft": error_text, "sender": "writer"}

def critic_node(state: NYRAState, config=None):
    """Evaluates the writer's draft for quality and accuracy."""
    draft = state.get("draft", "")
    messages = state["messages"]
    attempts = state.get("critic_attempts", 0) or 0
    
    system_msg = SystemMessage(
        content=f"You are the NYRA Critic. Evaluate the following draft response:\n\n{draft}\n\n"
                f"Does this draft directly and accurately answer the user's latest prompt based on the context? "
                f"Ensure there are no hallucinations."
    )
    
    evaluator_llm = llm_critic.with_structured_output(CriticReview)
    try:
        review = evaluator_llm.invoke([system_msg] + messages, config=config)
    except Exception as e:
        import logging
        logging.error(f"Critic LLM failed: {e}")
        # If the critic fails, we'll just assume it passed to avoid an infinite loop
        return {"messages": [AIMessage(content=draft)], "sender": "critic", "next_node": "FINISH", "critic_attempts": attempts + 1}
    
    if review.passed:
        # If passed, we finally append the draft to the message history as an AIMessage
        return {"messages": [AIMessage(content=draft)], "sender": "critic", "next_node": "FINISH", "critic_attempts": attempts + 1}
    else:
        # If failed, add the feedback to the context for the writer
        feedback_msg = HumanMessage(content=f"CRITIC FEEDBACK: The draft was rejected. Reason: {review.feedback}. Please rewrite it.")
        return {"messages": [feedback_msg], "sender": "critic", "next_node": "writer", "critic_attempts": attempts + 1}

# Create a lazy loader class that inherits from ToolNode but defers tool resolution
class LazyToolNode:
    def __init__(self, get_tools_func):
        self.get_tools_func = get_tools_func
        self._node = None
        
    def __call__(self, state, config=None):
        if not self._node:
            self._node = ToolNode(self.get_tools_func())
        return self._node.invoke(state, config=config)

tool_node = LazyToolNode(get_all_tools)

# Routing logic
def route_from_supervisor(state: NYRAState):
    return state.get("next_node", "writer")

def route_from_researcher(state: NYRAState):
    next_node = state.get("next_node")
    if next_node == "self_correct":
        return "self_correct"
    elif next_node == "writer":
        return "writer"
        
    messages = state["messages"]
    last_message = messages[-1]
    # If the researcher invoked a tool, go to tools
    if getattr(last_message, "tool_calls", None):
        return "tools"
    # Otherwise, it finished gathering info, go to writer
    return "writer"

def route_from_writer(state: NYRAState, config=None):
    thinking_level = config.get("configurable", {}).get("thinking_level", "medium") if config else "medium"
    attempts = state.get("critic_attempts", 0) or 0
    
    if thinking_level == "low":
        return "FINISH"
    elif thinking_level == "medium" and attempts >= 1:
        return "FINISH" # Only 1 critic loop for medium
    elif thinking_level == "high" and attempts >= 3:
        return "FINISH" # Max 3 critic loops for high
        
    return "critic"

def route_from_critic(state: NYRAState, config=None):
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
    "writer": "writer",
    "self_correct": "researcher"
})
graph.add_edge("tools", "researcher")

graph.add_conditional_edges("writer", route_from_writer, {
    "critic": "critic",
    "FINISH": END
})

graph.add_conditional_edges("critic", route_from_critic, {
    "writer": "writer",
    "FINISH": END
})

# Checkpointer
conn = sqlite3.connect("nyra_checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

nyra_graph = graph.compile(checkpointer=checkpointer)
