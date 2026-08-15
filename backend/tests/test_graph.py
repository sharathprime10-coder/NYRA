
import asyncio
import json
from app.graph.graph import nyra_graph
from langchain_core.messages import HumanMessage

async def test():
    config = {
        'configurable': {
            'thread_id': 'test-bug-125',
            'thinking_level': 'medium',
            'tone': 'default'
        }
    }
    
    msg = HumanMessage(content='explain ODE in 5 points')
    
    result = await nyra_graph.ainvoke(
        {'messages': [msg], 'user_id': 'test-user'},
        config=config
    )
    
    print('ALL MESSAGES IN RESULT:')
    for i, m in enumerate(result['messages']):
        print(f'[{i}] {type(m).__name__}: {repr(m.content)}')

asyncio.run(test())

