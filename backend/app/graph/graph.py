import sqlite3
from typing import Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, StateGraph, END

from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

from app.core.config import settings
from app.graph.state import NYRAState
from app.tools.registry import get_all_tools
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.core.llm_factory import get_robust_llm, get_writer_llm, get_critic_llm, get_frontier_llm, get_fast_llm, get_router_llm
import os

os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY
if settings.GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY

# Initialize the LLMs
llm_router = get_router_llm() # Supervisor (cheap, fast routing)
llm = get_frontier_llm() # Researcher (complex tool use)
llm_writer = get_writer_llm() # Writer (expressive, fast drafting)
llm_critic = get_critic_llm() # Critic (deep reasoning to catch hallucinations)

# Data Models for Routing
class Router(BaseModel):
    next_agent: Literal["researcher", "writer"] = Field(
        description="The next agent to route to. Choose 'researcher' if factual data/tools are needed. Choose 'writer' if drafting a response based on conversation context or casual chat."
    )

class CriticReview(BaseModel):
    passed: bool = Field(description="Set to true if the draft is good. Set to false if it has problems.")
    feedback: str = Field(default="", description="Feedback on why it failed, or empty if it passed.")
    
    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # Groq sometimes returns 'false'/'true' strings instead of booleans
        if isinstance(obj, dict) and isinstance(obj.get('passed'), str):
            obj['passed'] = obj['passed'].lower() in ('true', '1', 'yes')
        return super().model_validate(obj, *args, **kwargs)

def supervisor_node(state: NYRAState, config=None):
    """Orchestrator that routes to the appropriate specialist agent."""
    thinking_level = config.get("configurable", {}).get("thinking_level", "medium") if config else "medium"
    
    # If thinking level is low, bypass reasoning and immediately draft
    if thinking_level == "low":
        return {"sender": "supervisor", "next_node": "writer"}
    
    messages = state["messages"]
    
    # CRITICAL: If any system message mentions a document, ALWAYS route to researcher
    # so the rag_tool is used to actually read the document content
    for msg in messages:
        if isinstance(msg, SystemMessage) and any(kw in msg.content.lower() for kw in ["document", "pdf", "rag_tool", "attached"]):
            return {"sender": "supervisor", "next_node": "researcher"}
    
    # Also check user message for document/summarize keywords
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content.lower()
            break
    if any(kw in last_user_msg for kw in ["summarize", "pdf", "document", "file", "upload", "read", "extract", "according to"]):
        return {"sender": "supervisor", "next_node": "researcher"}
        
    system_msg = SystemMessage(
        content="You are the NYRA Orchestrator. Analyze the conversation. "
                "If the user asks a factual question, needs calculations, or document retrieval, route to 'researcher'. "
                "If the user asks a conversational question or asks to draft text based on history, route to 'writer'."
    )
    
    # Use structured output for routing
    router_llm_structured = llm_router.with_structured_output(Router)
    try:
        decision = router_llm_structured.invoke([system_msg] + messages[-5:], config=config)
        next_agent = decision.next_agent
    except Exception as e:
        import logging
        logging.error(f"Supervisor LLM failed: {e}")
        next_agent = "writer" # Fallback to writer if routing fails
    
    # We don't add the supervisor's thought to the message history, just route it
    return {"sender": "supervisor", "next_node": next_agent}

async def researcher_node(state: NYRAState, config=None):
    """Gathers facts and uses tools to build up a knowledge context."""
    messages = state["messages"]
    system_msg = SystemMessage(
        content="You are the NYRA Researcher. Your job is to gather accurate, detailed information to answer the user's query.\n"
                "Use the provided tools if needed. If no tools are needed, provide a detailed summary of your findings based on your knowledge.\n"
                "Do NOT write a conversational response to the user. Just gather the data.\n"
                "CRITICAL INSTRUCTION: You MUST use native JSON tool calling capabilities provided by the API. "
                "Your tool calls must be valid JSON."
    )
    
    # Late bind tools to ensure MCP is loaded with user_id
    user_id = config.get("configurable", {}).get("user_id") if config else None
    tools = await get_all_tools(user_id=user_id)
    
    # We must bind tools before creating fallbacks, so we get a fresh LLM instance here
    from app.core.llm_factory import get_frontier_llm
    llm_with_tools = get_frontier_llm(tools=tools)
    
    try:
        # Limit history to last 5 messages to save tokens
        response = await llm_with_tools.ainvoke([system_msg] + messages[-5:], config=config)
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
    tone = config.get("configurable", {}).get("tone", "default") if config else "default"
    messages = state["messages"]
    
    # Extract tool results to inject directly into the writer's context
    tool_context = ""
    low_confidence = False
    
    from langchain_core.messages import ToolMessage
    import json
    for msg in messages:
        if isinstance(msg, ToolMessage):
            try:
                data = json.loads(msg.content)
                if "confidence" in data and data["confidence"] == "Low":
                    low_confidence = True
                    
                if "context" in data:
                    context_str = "

".join(data["context"])
                    tool_context += f"
--- RETRIEVED DATA ---
{context_str}
"
                else:
                    tool_context += f"
--- RETRIEVED DATA ---
{msg.content}
"
            except Exception:
                tool_context += f"
--- RETRIEVED DATA ---
{msg.content}
"
    
    content = ""
    if tone == "sassy":
        content += (
            "You are NYRA - sharp, witty, and a little sassy, but never at the cost of "
            "being genuinely useful. Think 'brilliant friend who can't resist a dry remark,' "
            "not 'chatbot doing a bit.'

"
            "Personality rules:
"
            "- Default to helpful and direct. Sass is seasoning, not the meal.
"
            "- Dry wit, deadpan asides, gentle teasing about obviously bad ideas - yes.
"
            "- Mocking the user, being condescending, or being sarcastic about something "
            "they're genuinely struggling with - no.
"
            "- If the user's message signals stress, frustration, or something serious "
            "(exams, deadlines, errors blocking their work, personal topics), drop the "
            "sass entirely and just help.
"
            "- Never let personality replace accuracy - a sassy wrong answer is still wrong.
"
            "- Keep it to a line or two of flavor, not a running commentary track.

"
            "Examples of the tone:
"
            "- Instead of 'I don't have that information': 'That one's above my pay grade - "
            "I don't have access to that.'
"
            "- Instead of 'That's incorrect': 'Bold claim, but the data disagrees with you.'

"
        )
        
    content += "You are the NYRA Writer. Your job is to draft a helpful, professional, and accurate response to the user. "
    content += "Use the conversation history and the RETRIEVED DATA below to write your response. Output your response clearly in markdown.
"
    
    if low_confidence:
        content += "CRITICAL: The retrieved data DOES NOT contain sufficient information to answer the user's question. You MUST explicitly state that the documents do not have enough information, rather than guessing or answering from general knowledge. Be polite but firm about this limitation.
"
    else:
        content += "CRITICAL: You MUST directly answer the user's question using the retrieved data. Do NOT tell the user to summarize it themselves.
"
        content += "CRITICAL: Incorporate the information seamlessly into your answer as if it were your own knowledge. Do NOT mention your internal tools, 'rag_tool', or your retrieval process to the user.
"
        content += "CRITICAL GROUNDING INSTRUCTION: For EVERY factual sentence you write that is sourced from the RETRIEVED DATA, you MUST append an inline citation marker (e.g. [1], [2]) indicating the source. If a sentence is general knowledge and not found in the documents, explicitly flag it as general knowledge and do not use a citation marker.
"
    
    if tool_context:
        content += f"
{tool_context}"
    
    system_msg = SystemMessage(content=content)
    
    try:
        response = llm_writer.invoke([system_msg] + messages[-10:], config=config)
        return {"messages": [response], "sender": "writer"}
    except Exception as e:
        import logging
        logging.error(f"Writer LLM failed: {e}")
        return {"messages": [AIMessage(content=f"Error generating response: {str(e)}")], "sender": "writer"}

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
    tool_invoked = state.get("tool_invoked", False)
    
    if thinking_level == "low":
        return "FINISH"
    elif thinking_level == "medium" and not tool_invoked:
        return "FINISH" # Skip critic for medium conversational turns without factual tool data
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

from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

nyra_graph = graph.compile(checkpointer=checkpointer)
