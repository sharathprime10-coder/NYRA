import json
import logging
import os
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.llm_factory import (
    get_critic_llm,
    get_frontier_llm,
    get_router_llm,
    get_writer_llm,
)
from app.graph.state import NYRAState
from app.tools.registry import get_all_tools

os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY
if settings.GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY

# Initialize the LLMs
llm_router = get_router_llm()  # Supervisor (cheap, fast routing)
llm = get_frontier_llm()  # Researcher (complex tool use)
llm_writer = get_writer_llm()  # Writer (expressive, fast drafting)
llm_critic = get_critic_llm()  # Critic (deep reasoning to catch hallucinations)


# Data Models for Routing
class Router(BaseModel):
    next_agent: Literal["researcher", "writer"] = Field(
        description=(
            "The next agent to route to. Choose 'researcher' if factual data/tools are needed. "
            "Choose 'writer' if drafting a response based on conversation context or casual chat."
        )
    )


class CriticReview(BaseModel):
    passed: bool = Field(
        description="Set to true if the draft is good. Set to false if it has problems."
    )
    feedback: str = Field(
        default="", description="Feedback on why it failed, or empty if it passed."
    )

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # Groq sometimes returns 'false'/'true' strings instead of booleans
        if isinstance(obj, dict) and isinstance(obj.get("passed"), str):
            obj["passed"] = obj["passed"].lower() in ("true", "1", "yes")
        return super().model_validate(obj, *args, **kwargs)


def supervisor_node(state: NYRAState, config=None):
    """Orchestrator that routes to the appropriate specialist agent."""
    thinking_level = (
        config.get("configurable", {}).get("thinking_level", "medium")
        if config
        else "medium"
    )

    # If thinking level is low, bypass reasoning and immediately draft
    if thinking_level == "low":
        return {"sender": "supervisor", "next_node": "writer"}

    messages = state["messages"]

    # CRITICAL: If any system message mentions a document, ALWAYS route to researcher
    # so the rag_tool is used to actually read the document content
    for msg in messages:
        if isinstance(msg, SystemMessage) and any(
            kw in msg.content.lower()
            for kw in ["document", "pdf", "rag_tool", "attached"]
        ):
            return {"sender": "supervisor", "next_node": "researcher"}

    # Also check user message for document/summarize keywords
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content.lower()
            break
    if any(
        kw in last_user_msg
        for kw in [
            "summarize",
            "pdf",
            "document",
            "file",
            "upload",
            "read",
            "extract",
            "according to",
        ]
    ):
        return {"sender": "supervisor", "next_node": "researcher"}

    system_msg = SystemMessage(
        content=(
            "You are the NYRA Orchestrator. Analyze the conversation. "
            "If the user asks a factual question, needs calculations, or document retrieval, route to 'researcher'. "
            "If the user asks a conversational question or asks to draft text based on history, route to 'writer'."
        )
    )

    # Use structured output for routing
    router_llm_structured = llm_router.with_structured_output(Router)
    try:
        decision = router_llm_structured.invoke(
            [system_msg] + messages[-5:], config=config
        )
        next_agent = decision.next_agent
    except Exception as e:
        logging.error(f"Supervisor LLM failed: {e}")
        next_agent = "writer"  # Fallback to writer if routing fails

    # We don't add the supervisor's thought to the message history, just route it
    return {"sender": "supervisor", "next_node": next_agent}


async def researcher_node(state: NYRAState, config=None):
    """Gathers facts and uses tools to build up a knowledge context."""
    messages = state["messages"]
    system_msg = SystemMessage(
        content=(
            "You are the NYRA Researcher. Your job is to gather accurate, detailed information to answer the user's query.\n"
            "Use the provided tools if needed. If no tools are needed, provide a detailed summary of your findings based on your knowledge.\n"
            "Do NOT write a conversational response to the user. Just gather the data.\n"
            "CRITICAL INSTRUCTION: You MUST use native JSON tool calling capabilities provided by the API. "
            "Your tool calls must be valid JSON."
        )
    )

    # Late bind tools to ensure MCP is loaded with user_id
    user_id = config.get("configurable", {}).get("user_id") if config else None
    tools = await get_all_tools(user_id=user_id)

    # We must bind tools before creating fallbacks, so we get a fresh LLM instance here
    llm_with_tools = get_frontier_llm(tools=tools)

    try:
        # Limit history to last 5 messages to save tokens
        response = await llm_with_tools.ainvoke(
            [system_msg] + messages[-5:], config=config
        )
        return {"messages": [response], "sender": "researcher", "error_retries": 0}
    except Exception as e:
        logging.error(f"Researcher LLM failed: {e}")

        # Auto-healing loop
        retries = state.get("error_retries", 0) or 0
        if retries < 3:
            error_msg = HumanMessage(
                content=(
                    f"SYSTEM ERROR: Your previous tool call failed with the following error: {str(e)}. "
                    "Please analyze the error and try again. Ensure you are using strict JSON formatting "
                    "for your tool calls without any markdown tags."
                )
            )
            return {
                "messages": [error_msg],
                "sender": "researcher",
                "error_retries": retries + 1,
                "next_node": "self_correct",
            }
        else:
            return {
                "messages": [
                    AIMessage(
                        content=f"Error gathering data after multiple attempts: {str(e)}"
                    )
                ],
                "sender": "researcher",
                "next_node": "writer",
            }


async def writer_node(state: NYRAState, config=None):
    """Drafts the final response to the user."""
    thinking_level = (
        config.get("configurable", {}).get("thinking_level", "medium")
        if config
        else "medium"
    )  # noqa: F841
    tone = (
        config.get("configurable", {}).get("tone", "default") if config else "default"
    )
    messages = state["messages"]

    # Extract tool results to inject directly into the writer's context
    tool_context = ""
    low_confidence = False

    for msg in messages:
        if isinstance(msg, ToolMessage):
            try:
                data = json.loads(msg.content)
                if "confidence" in data and data["confidence"] == "Low":
                    low_confidence = True

                if "context" in data:
                    context_str = "\n\n".join(data["context"])
                    tool_context += f"\n--- RETRIEVED DATA ---\n{context_str}\n"
                else:
                    tool_context += f"\n--- RETRIEVED DATA ---\n{msg.content}\n"
            except Exception:
                tool_context += f"\n--- RETRIEVED DATA ---\n{msg.content}\n"

    content = ""
    if tone == "sassy":
        content += (
            "You are NYRA - sharp, witty, and a little sassy, but never at the cost of "
            "being genuinely useful. Think 'brilliant friend who can't resist a dry remark,' "
            "not 'chatbot doing a bit.'\n\n"
            "Personality rules:\n"
            "- Default to helpful and direct. Sass is seasoning, not the meal.\n"
            "- Dry wit, deadpan asides, gentle teasing about obviously bad ideas - yes.\n"
            "- Mocking the user, being condescending, or being sarcastic about something "
            "they're genuinely struggling with - no.\n"
            "- If the user's message signals stress, frustration, or something serious "
            "(exams, deadlines, errors blocking their work, personal topics), drop the "
            "sass entirely and just help.\n"
            "- Never let personality replace accuracy - a sassy wrong answer is still wrong.\n"
            "- Keep it to a line or two of flavor, not a running commentary track.\n\n"
            "Examples of the tone:\n"
            "- Instead of 'I don't have that information': 'That one's above my pay grade - "
            "I don't have access to that.'\n"
            "- Instead of 'That's incorrect': 'Bold claim, but the data disagrees with you.'\n\n"
        )

    content += "You are the NYRA Writer. Your job is to draft a helpful, professional, and accurate response to the user. "
    content += "Use the conversation history and the RETRIEVED DATA below to write your response. Output your response clearly in markdown.\n"

    if low_confidence:
        content += (
            "CRITICAL: The retrieved data DOES NOT contain sufficient information to answer the user's question. "
            "You MUST explicitly state that the documents do not have enough information, rather than guessing or answering "
            "from general knowledge. Be polite but firm about this limitation.\n"
        )
    else:
        content += "CRITICAL: You MUST directly answer the user's question using the retrieved data. Do NOT tell the user to summarize it themselves.\n"
        content += "CRITICAL: Incorporate the information seamlessly into your answer as if it were your own knowledge. Do NOT mention your internal tools, 'rag_tool', or your retrieval process to the user.\n"
        content += (
            "CRITICAL GROUNDING INSTRUCTION: For EVERY factual sentence you write that is sourced from the RETRIEVED DATA, "
            "you MUST append an inline citation marker (e.g. [1], [2]) indicating the source. If a sentence is general "
            "knowledge and not found in the documents, explicitly flag it as general knowledge and do not use a citation marker.\n"
        )

    if tool_context:
        content += f"\n{tool_context}"

    system_msg = SystemMessage(content=content)

    try:
        response = await llm_writer.ainvoke(
            [system_msg] + messages[-10:], config=config
        )
        return {"draft": response.content, "sender": "writer"}
    except Exception as e:
        logging.error(f"Writer LLM failed: {e}")
        error_text = f"Error generating response: {str(e)}"
        return {
            "messages": [AIMessage(content=error_text)],
            "draft": error_text,
            "sender": "writer",
        }


def critic_node(state: NYRAState, config=None):
    """Evaluates the writer's draft for quality and accuracy."""
    draft = state.get("draft", "")
    messages = state["messages"]
    attempts = state.get("critic_attempts", 0) or 0

    system_msg = SystemMessage(
        content=(
            f"You are the NYRA Critic. Evaluate the following draft response:\n\n{draft}\n\n"
            "Does this draft directly and accurately answer the user's latest prompt based on the context? "
            "Ensure there are no hallucinations."
        )
    )

    evaluator_llm = llm_critic.with_structured_output(CriticReview)
    try:
        review = evaluator_llm.invoke([system_msg] + messages[-10:], config=config)

        if review.passed:
            # If passed, we finally append the draft to the message history as an AIMessage
            return {
                "messages": [AIMessage(content=draft)],
                "sender": "critic",
                "next_node": "FINISH",
            }
        else:
            # If failed, add the feedback to the context for the writer
            feedback_msg = HumanMessage(
                content=f"CRITIC FEEDBACK: The draft was rejected. Reason: {review.feedback}. Please rewrite it."
            )
            return {
                "messages": [feedback_msg],
                "sender": "critic",
                "next_node": "writer",
                "critic_attempts": attempts + 1,
            }
    except Exception as e:
        # Fallback if critic fails
        logging.error(f"Critic LLM failed: {e}")
        return {
            "messages": [AIMessage(content=draft)],
            "sender": "critic",
            "next_node": "FINISH",
        }


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
    thinking_level = (
        config.get("configurable", {}).get("thinking_level", "medium")
        if config
        else "medium"
    )
    attempts = state.get("critic_attempts", 0) or 0
    tool_invoked = state.get("tool_invoked", False)

    if thinking_level == "low":
        return "FINISH"
    elif thinking_level == "medium" and not tool_invoked:
        return "FINISH"  # Skip critic for medium conversational turns without factual tool data
    elif thinking_level == "medium" and attempts >= 1:
        return "FINISH"  # Only 1 critic loop for medium
    elif thinking_level == "high" and attempts >= 3:
        return "FINISH"  # Max 3 critic loops for high

    return "critic"


def route_from_critic(state: NYRAState, config=None):  # noqa: ARG001
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

graph.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "researcher": "researcher",
        "writer": "writer",
    },
)

graph.add_conditional_edges(
    "researcher",
    route_from_researcher,
    {
        "tools": "tools",
        "writer": "writer",
        "self_correct": "researcher",
    },
)
graph.add_edge("tools", "researcher")

graph.add_conditional_edges(
    "writer",
    route_from_writer,
    {
        "critic": "critic",
        "FINISH": END,
    },
)

graph.add_conditional_edges(
    "critic",
    route_from_critic,
    {
        "writer": "writer",
        "FINISH": END,
    },
)

checkpointer = MemorySaver()
nyra_graph = graph.compile(checkpointer=checkpointer)
