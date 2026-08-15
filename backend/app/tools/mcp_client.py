import asyncio
import os
import sys
from contextlib import AsyncExitStack

from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# Cache user sessions so we don't start a new process on every single turn
# Key: user_id -> Value: (AsyncExitStack, tools_list)
_user_sessions = {}


async def _init_user_mcp(user_id: int):
    """Async helper to initialize servers for a specific user."""
    exit_stack = AsyncExitStack()
    user_tools = []

    # 1. Filesystem Server (Scoped to user_id)
    user_docs_dir = os.path.abspath(f"./uploaded_docs/{user_id}")
    os.makedirs(user_docs_dir, exist_ok=True)

    # 2. Notes Server
    notes_server_path = os.path.abspath("./mcp_servers/notes_server.py")

    servers = [
        {
            "name": "filesystem",
            "params": StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", user_docs_dir],
            ),
        },
        {
            "name": "notes",
            "params": StdioServerParameters(
                command=sys.executable,
                args=[notes_server_path],
            ),
        },
    ]

    for server_config in servers:
        try:
            read, write = await exit_stack.enter_async_context(
                stdio_client(server_config["params"])
            )
            session = await exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            # Load tools from this specific server
            tools = await load_mcp_tools(session)
            # Annotate tools to log which server they came from
            for t in tools:
                t.description = f"[{server_config['name']}] " + t.description

            user_tools.extend(tools)
            print(f"Loaded {len(tools)} tools from MCP server: {server_config['name']}")
        except Exception as e:
            print(f"Failed to initialize MCP server {server_config['name']}: {e}")
            # Graceful degradation: continue with the remaining servers

    return exit_stack, user_tools


async def get_mcp_tools(user_id: int):
    """Returns the MCP tools scoped to the specific user. Initializes asynchronously if needed."""
    if user_id not in _user_sessions:
        try:
            exit_stack, tools = await _init_user_mcp(user_id)
            _user_sessions[user_id] = (exit_stack, tools)
        except Exception as e:
            print(f"Error loading MCP tools for user {user_id}: {e}")
            return []

    return _user_sessions[user_id][1]


async def cleanup_mcp():
    """Cleans up all MCP client connections across all users."""
    for user_id, (exit_stack, tools) in _user_sessions.items():
        try:
            await asyncio.wait_for(exit_stack.aclose(), timeout=2.0)
        except Exception as e:
            print(f"Error closing MCP session for user {user_id}: {e}")
    _user_sessions.clear()


async def initialize_mcp():
    """No-op global startup. We lazily load per-user now."""
