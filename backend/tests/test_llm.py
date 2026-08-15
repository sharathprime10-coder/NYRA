
import asyncio
from app.core.llm_factory import get_frontier_llm
from app.tools.registry import get_all_tools
from langchain_core.messages import HumanMessage

async def test():
    tools = await get_all_tools()
    llm = get_frontier_llm(tools=tools)
    res = await llm.ainvoke([HumanMessage(content='What is 2+2?')])
    print(res)

asyncio.run(test())

