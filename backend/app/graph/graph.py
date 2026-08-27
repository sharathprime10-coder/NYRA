import json
import logging
import os
import time
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
    path: Literal["simple", "deep"] = Field(
        description=(
            "The path to route to. Choose 'simple' if it is a general knowledge question, "
            "conversational, or answerable without the user's uploaded documents or tools. "
            "Choose 'deep' if it requires retrieval from uploaded documents or tool use."
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
    start = time.time()
    thinking_level = (
        config.get("configurable", {}).get("thinking_level", "medium")
        if config
        else "medium"
    )

    # If thinking level is low, bypass reasoning and immediately draft
    if thinking_level == "low":
        return {"sender": "supervisor", "next_node": "writer", "routing_path": "simple"}

    messages = state["messages"]

    # CRITICAL: If any system message mentions a document, ALWAYS route to researcher
    # so the rag_tool is used to actually read the document content
    for msg in messages:
        if isinstance(msg, SystemMessage) and any(
            kw in msg.content.lower()
            for kw in ["document", "pdf", "rag_tool", "attached"]
        ):
            return {
                "sender": "supervisor",
                "next_node": "researcher",
                "routing_path": "deep",
            }

    # Also check user message for document/summarize keywords
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content.lower()
            break
    has_doc_filter = (
        config
        and config.get("configurable", {}).get("filters", {}).get("document_id")
        is not None
    )

    if has_doc_filter or any(
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
        return {
            "sender": "supervisor",
            "next_node": "researcher",
            "routing_path": "deep",
        }

    system_msg = SystemMessage(
        content=(
            "You are the NYRA Orchestrator. Analyze the conversation. "
            "If the user asks a factual question, needs calculations, or document retrieval, route to 'deep'. "
            "If the user asks a conversational question or asks to draft text based on history, route to 'simple'."
        )
    )

    # Use structured output for routing
    router_llm_structured = llm_router.with_structured_output(Router)
    try:
        decision = router_llm_structured.invoke([system_msg] + messages, config=config)
        routing_path = decision.path
    except Exception as e:
        logging.error(f"Supervisor LLM failed: {e}")
        routing_path = "simple"  # Fallback to simple writer path if routing fails

    next_agent = "writer" if routing_path == "simple" else "researcher"

    # We don't add the supervisor's thought to the message history, just route it
    duration = (time.time() - start) * 1000
    logging.info(
        "agent_node_completed",
        extra={
            "event": "agent_node_completed",
            "node": "supervisor",
            "duration_ms": round(duration, 1),
            "routing_path": routing_path,
        },
    )
    return {
        "sender": "supervisor",
        "next_node": next_agent,
        "routing_path": routing_path,
    }


async def researcher_node(state: NYRAState, config=None):
    """Gathers facts and uses tools to build up a knowledge context."""
    start = time.time()
    messages = state["messages"]

    # Track research iterations for the hard cap
    iterations = (state.get("research_iterations") or 0) + 1
    logging.info(
        "researcher_iteration",
        extra={
            "event": "researcher_iteration",
            "research_iterations": iterations,
        },
    )

    system_msg = SystemMessage(
        content=(
            "You are the NYRA Researcher. Your job is to gather accurate, detailed information to answer the user's query.\n"
            "Use the provided tools if needed. If no tools are needed, provide a detailed summary of your findings based on your knowledge.\n"
            "Do NOT write a conversational response to the user. Just gather the data.\n"
            "CRITICAL INSTRUCTION: You MUST use native JSON tool calling capabilities provided by the API. "
            "Your tool calls must be valid JSON.\n"
            "IMPORTANT: If a tool returns an error saying 'Do NOT retry your search', do NOT call that tool again. "
            "Instead, report the failure and move on."
        )
    )

    # Late bind tools to ensure MCP is loaded with user_id
    user_id = config.get("configurable", {}).get("user_id") if config else None
    tools = await get_all_tools(user_id=user_id)

    # We must bind tools before creating fallbacks, so we get a fresh LLM instance here
    llm_with_tools = get_frontier_llm(tools=tools)

    try:
        # Pass the full history. Slicing with [-5:] can split a ToolMessage from its AIMessage
        # and cause a strict API validation error in Gemini.
        response = await llm_with_tools.ainvoke([system_msg] + messages, config=config)
        duration = (time.time() - start) * 1000
        logging.info(
            "agent_node_completed",
            extra={
                "event": "agent_node_completed",
                "node": "researcher",
                "duration_ms": round(duration, 1),
                "research_iterations": iterations,
            },
        )
        return {
            "messages": [response],
            "sender": "researcher",
            "error_retries": 0,
            "research_iterations": iterations,
        }
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
                "research_iterations": iterations,
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
                "research_iterations": iterations,
                "next_node": "writer",
            }


async def writer_node(state: NYRAState, config=None):
    """Drafts the final response to the user."""
    start = time.time()
    thinking_level = (
        config.get("configurable", {}).get("thinking_level", "medium")
        if config
        else "medium"
    )  # noqa: F841
    tone = (
        config.get("configurable", {}).get("tone", "default") if config else "default"
    )
    messages = state["messages"]
    retrieval_failed = state.get("retrieval_failed") or False

    # Detect retrieval failure from tool messages ("Do NOT retry" error from rag_tool)
    # This catches the case where rag_tool returned an explicit no-results error
    for msg in messages:
        if isinstance(msg, ToolMessage):
            try:
                content = msg.content
                if isinstance(content, str) and "Do NOT retry" in content:
                    retrieval_failed = True
                    break
                data = json.loads(content) if isinstance(content, str) else content
                if isinstance(data, dict) and "Do NOT retry" in str(
                    data.get("error", "")
                ):
                    retrieval_failed = True
                    break
            except (json.JSONDecodeError, TypeError):
                pass

    # Also check research iteration cap
    iterations = state.get("research_iterations") or 0
    if iterations >= 2:
        # Check if we actually got useful content despite hitting the cap
        has_content = False
        for msg in messages:
            if isinstance(msg, ToolMessage):
                try:
                    data = (
                        json.loads(msg.content)
                        if isinstance(msg.content, str)
                        else msg.content
                    )
                    if (
                        isinstance(data, dict)
                        and data.get("context")
                        and len(data["context"]) > 0
                    ):
                        has_content = True
                        break
                except (json.JSONDecodeError, TypeError):
                    pass
        if not has_content:
            retrieval_failed = True

    if retrieval_failed:
        logging.warning(
            "writer_retrieval_failed",
            extra={
                "event": "writer_retrieval_failed",
                "research_iterations": iterations,
            },
        )

    # Extract tool results to inject directly into the writer's context
    tool_context = ""
    low_confidence = False

    for msg in messages:
        if isinstance(msg, ToolMessage):
            try:
                data = json.loads(msg.content)

                # rag_tool returns {"context": {... dict from query_knowledge_base ...}}
                if "context" in data and isinstance(data["context"], dict):
                    context_dict = data["context"]
                    if (
                        "confidence" in context_dict
                        and context_dict["confidence"] == "Low"
                    ):
                        low_confidence = True

                    sources = context_dict.get("sources", [])
                    if sources:
                        context_str = "\n\n".join(
                            [s.get("content", "") for s in sources]
                        )
                        tool_context += f"\n--- RETRIEVED DATA ---\n{context_str}\n"
                    else:
                        tool_context += "\n--- RETRIEVED DATA ---\nNo sources found.\n"
                elif "context" in data and isinstance(data["context"], list):
                    # Fallback for other tools that might return a list of strings
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

    if retrieval_failed:
        content += (
            "CRITICAL: The document retrieval FAILED — no relevant content was found in the user's uploaded documents. "
            "You MUST tell the user that you could not find relevant information in their document(s). "
            "Do NOT attempt to answer from general knowledge, do NOT guess, and do NOT make up content. "
            "Simply state that the information was not found in the uploaded document(s) and suggest they try rephrasing "
            "their question or verifying the document was uploaded correctly. Be polite but firm.\n"
        )
    elif low_confidence:
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
        llm_config = {**config} if config else {}
        llm_config["tags"] = llm_config.get("tags", []) + ["writer"]

        # Append a HumanMessage to prevent Gemini's "model prefilling" error
        writer_prompt = HumanMessage(
            content="Based on the context and instructions provided, please write the final response."
        )

        # Filter out tool interactions from the conversation history to prevent Gemini validation errors
        # (Gemini strictly requires alternating roles and matching tool calls/responses)
        clean_history = []
        for m in messages:
            if isinstance(m, ToolMessage):
                continue
            elif isinstance(m, AIMessage):
                # If it's an AIMessage with tool calls, we strip the tool calls so it's just text (if any)
                if getattr(m, "tool_calls", None) or getattr(
                    m, "invalid_tool_calls", None
                ):
                    if m.content:
                        clean_history.append(AIMessage(content=m.content))
                    continue
                clean_history.append(m)
            else:
                clean_history.append(m)

        draft = ""
        async for chunk in llm_writer.astream(
            [system_msg] + clean_history + [writer_prompt], config=llm_config
        ):
            content = chunk.content
            if isinstance(content, str):
                draft += content
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        draft += item["text"]
                    elif isinstance(item, str):
                        draft += item

        duration = (time.time() - start) * 1000
        logging.info(
            "agent_node_completed",
            extra={
                "event": "agent_node_completed",
                "node": "writer",
                "duration_ms": round(duration, 1),
            },
        )
        return {"draft": draft, "sender": "writer"}
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
    start = time.time()
    draft = state.get("draft", "")
    messages = state["messages"]
    attempts = state.get("critic_attempts", 0) or 0

    if attempts >= 1:
        logging.warning("Critic loop cap reached. Approving draft to prevent latency.")
        duration = (time.time() - start) * 1000
        logging.info(
            "agent_node_completed",
            extra={
                "event": "agent_node_completed",
                "node": "critic",
                "duration_ms": round(duration, 1),
                "cap_reached": True,
            },
        )
        return {
            "messages": [AIMessage(content=draft)],
            "sender": "critic",
            "next_node": "FINISH",
        }

    system_msg = SystemMessage(
        content=(
            f"You are the NYRA Critic. Evaluate the following draft response:\n\n{draft}\n\n"
            "Does this draft directly and accurately answer the user's latest prompt based on the context? "
            "Ensure there are no hallucinations."
        )
    )

    evaluator_llm = llm_critic.with_structured_output(CriticReview)
    try:
        # Append a HumanMessage at the end to prevent Gemini "model prefilling" error
        eval_prompt = HumanMessage(
            content="Based on the conversation above, please evaluate the draft as instructed."
        )

        # Pass full history to prevent Gemini API strict validation errors caused by slicing
        review = evaluator_llm.invoke(
            [system_msg] + messages + [eval_prompt], config=config
        )

        if review.passed:
            # If passed, we finally append the draft to the message history as an AIMessage
            duration = (time.time() - start) * 1000
            logging.info(
                "agent_node_completed",
                extra={
                    "event": "agent_node_completed",
                    "node": "critic",
                    "duration_ms": round(duration, 1),
                },
            )
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


async def tool_node(state: NYRAState, config=None):
    from langchain_core.messages import ToolMessage

    user_id = None
    if config and "configurable" in config:
        user_id = config["configurable"].get("user_id")

    tools = await get_all_tools(user_id=user_id)
    tools_by_name = {tool.name: tool for tool in tools}

    last_message = state["messages"][-1]
    results = []

    for tool_call in getattr(last_message, "tool_calls", []):
        tool = tools_by_name.get(tool_call["name"])
        if tool:
            try:
                # Some tools might be sync, some async, use invoke which handles both
                result = tool.invoke(tool_call["args"], config=config)
                results.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )
            except Exception as e:
                results.append(
                    ToolMessage(
                        content=f"Error: {str(e)}", tool_call_id=tool_call["id"]
                    )
                )
        else:
            results.append(
                ToolMessage(
                    content=f"Tool {tool_call['name']} not found",
                    tool_call_id=tool_call["id"],
                )
            )

    return {"messages": results}


def route_from_supervisor(state: NYRAState):
    return state.get("next_node", "writer")


def route_from_researcher(state: NYRAState):
    next_node = state.get("next_node")
    if next_node == "self_correct":
        return "self_correct"
    elif next_node == "writer":
        return "writer"

    # Hard cap: stop after 2 research iterations to prevent infinite retry loops
    iterations = state.get("research_iterations") or 0
    if iterations >= 2:
        logging.warning(
            "research_cap_reached",
            extra={
                "event": "research_cap_reached",
                "research_iterations": iterations,
            },
        )
        # Route to writer with retrieval_failed flag
        return "writer"

    messages = state["messages"]
    last_message = messages[-1]

    # Check if the last tool result was a "do not retry" error from rag_tool
    # If so, skip further tool calls and go straight to writer with failure flag
    if isinstance(last_message, ToolMessage):
        try:
            data = (
                json.loads(last_message.content)
                if isinstance(last_message.content, str)
                else last_message.content
            )
            if isinstance(data, dict) and "Do NOT retry" in str(data.get("error", "")):
                logging.info(
                    "rag_no_retry_detected",
                    extra={"event": "rag_no_retry_detected"},
                )
                return "writer"
        except (json.JSONDecodeError, TypeError):
            if (
                isinstance(last_message.content, str)
                and "Do NOT retry" in last_message.content
            ):
                return "writer"

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

    if thinking_level == "low":
        return "FINISH"

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
