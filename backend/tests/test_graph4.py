import asyncio

from langchain_core.messages import HumanMessage

from app.graph.graph import nyra_graph


async def test():
    config = {
        "configurable": {
            "thread_id": "test-bug-129",
            "thinking_level": "medium",
            "tone": "default",
        }
    }
    msg = HumanMessage(content="use the rag_tool to explain ODE in 5 points")
    result = await nyra_graph.ainvoke(
        {"messages": [msg], "user_id": "test-user", "tool_invoked": True}, config=config
    )
    print("ALL MESSAGES IN RESULT:")
    for i, m in enumerate(result["messages"]):
        print(
            f'[{i}] {type(m).__name__}: {m.content!r} (name: {getattr(m, "name", None)})'
        )


asyncio.run(test())
