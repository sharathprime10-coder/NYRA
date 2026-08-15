from mcp.server import Server
import mcp.types as types
from pydantic import AnyUrl

# Minimal memory-backed notes store for demonstration
# In production, this would use the database (user_id scoped)
_notes = {}

# We create the server
app = Server("nyra-notes")

@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl("note://internal/system"),
            name="System Notes",
            mimeType="text/plain",
            description="System-level notes and bookmarks"
        )
    ]

@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    if str(uri) == "note://internal/system":
        return "Notes server is online. No system notes saved yet."
    raise ValueError(f"Unknown resource: {uri}")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="save_note",
            description="Save a markdown note or bookmark for the user. Useful when the user asks you to remember something.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the note"},
                    "content": {"type": "string", "description": "Markdown content to save"}
                },
                "required": ["title", "content"]
            }
        ),
        types.Tool(
            name="list_notes",
            description="List all saved notes.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "save_note":
        title = arguments["title"]
        content = arguments["content"]
        _notes[title] = content
        return [types.TextContent(type="text", text=f"Successfully saved note: {title}")]
        
    if name == "list_notes":
        if not _notes:
            return [types.TextContent(type="text", text="No notes saved yet.")]
        
        result = "Saved Notes:\n"
        for title, content in _notes.items():
            result += f"- **{title}**: {content}\n"
        return [types.TextContent(type="text", text=result)]
        
    raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    from mcp.server.stdio import stdio_server
    import asyncio
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
            
    asyncio.run(main())
