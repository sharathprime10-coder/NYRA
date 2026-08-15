import os

from langchain_core.tools import BaseTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPAdapter:
    """
    Adapter to bridge Model Context Protocol (MCP) servers into LangGraph tools.
    Currently a stub to be expanded when external MCP servers are registered in .env.
    """

    def __init__(self):
        self.servers: dict[str, StdioServerParameters] = {}
        self._load_from_env()

    def _load_from_env(self):
        """
        Load MCP server configurations from environment variables.
        Format expected: MCP_SERVER_<NAME>="command arg1 arg2"
        """
        for key, value in os.environ.items():
            if key.startswith("MCP_SERVER_"):
                name = key.replace("MCP_SERVER_", "").lower()
                parts = value.split()
                if parts:
                    self.servers[name] = StdioServerParameters(
                        command=parts[0], args=parts[1:], env=None
                    )

    async def get_tools_from_server(self, server_name: str) -> list[BaseTool]:
        """
        Connects to an MCP server via stdio and returns its tools mapped to LangChain BaseTools.
        """
        if server_name not in self.servers:
            return []

        server_params = self.servers[server_name]
        tools = []

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    # List tools from the MCP server
                    result = await session.list_tools()
                    # Mapping logic would go here
        except Exception as e:
            print(f"Failed to connect to MCP server {server_name}: {e}")

        return tools


mcp_adapter = MCPAdapter()
