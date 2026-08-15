import asyncio
from app.graph.graph import nyra_graph
from langchain_core.messages import HumanMessage

async def test():
    config = {
        'configurable': {
            'thread_id': 'test-bug-128',
            'thinking_level': 'medium',
            'tone': 'default'
        }
    }
    msg = HumanMessage(content='explain ODE in 5 points')
    result = await nyra_graph.ainvoke({'messages': [msg], 'user_id': 'test-user'}, config=config)
    print('ALL MESSAGES IN RESULT:')
    for i, m in enumerate(result['messages']):
        print(f'[{i}] {type(m).__name__}: {repr(m.content)} (name: {getattr(m, "name", None)})')
    print('SENDER:', result.get('sender'))
    print('NEXT_NODE:', result.get('next_node'))
    print('TOOL_INVOKED:', result.get('tool_invoked'))
asyncio.run(test())
