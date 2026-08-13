from contextlib import AsyncExitStack
import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from langchain_mcp_adapters.tools import load_mcp_tools

# Global state for MCP tools and lifecycle
_mcp_tools = []
_exit_stack = AsyncExitStack()

async def initialize_mcp():
    """Initializes the MCP client and loads tools globally."""
    global _mcp_tools, _exit_stack
    
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "./uploaded_docs"],
    )
    
    try:
        # Start the stdio transport
        read, write = await _exit_stack.enter_async_context(stdio_client(server_params))
        
        # Start the MCP session
        session = await _exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        
        # Load tools into LangChain format
        _mcp_tools = await load_mcp_tools(session)
        print(f"Successfully loaded {len(_mcp_tools)} MCP tools!")
    except Exception as e:
        print(f"Failed to initialize MCP: {e}")

async def cleanup_mcp():
    """Cleans up the MCP client connections."""
    global _exit_stack
    await _exit_stack.aclose()

def get_mcp_tools():
    """Returns the globally loaded MCP tools."""
    return _mcp_tools
