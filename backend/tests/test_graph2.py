import asyncio

from langchain_core.messages import HumanMessage

from app.graph.graph import nyra_graph


async def test():
    config = {
        "configurable": {
            "thread_id": "test-bug-127",
            "thinking_level": "medium",
            "tone": "default",
        }
    }
    msg = HumanMessage(content="hello world")
    result = await nyra_graph.ainvoke({"messages": [msg]}, config=config)
    print("ALL MESSAGES IN RESULT:")
    for i, m in enumerate(result["messages"]):
        print(f"[{i}] {type(m).__name__}: {m.content!r}")


asyncio.run(test())
