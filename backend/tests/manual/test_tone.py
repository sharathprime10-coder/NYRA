import asyncio

from langchain_core.messages import HumanMessage

from app.graph.graph import nyra_graph


async def test():
    config = {
        "configurable": {
            "thread_id": "test-sassy-124",
            "thinking_level": "high",
            "tone": "sassy",
        }
    }

    msg = HumanMessage(content="Do you think aliens built the pyramids?")

    result = await nyra_graph.ainvoke(
        {"messages": [msg], "user_id": "test-user"}, config=config
    )

    print("FINAL RESPONSE:")
    print(result["messages"][-1].content)


asyncio.run(test())
