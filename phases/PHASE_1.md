# Phase 1: MCP Server Skeleton with Ping Tool

## What Was Implemented

A minimal [fastmcp](https://github.com/jlowin/fastmcp) MCP server in `src/server.py` with:

- **`FastMCP` app** named `"code-analyzer"` — this name is surfaced to MCP clients when they connect.
- **`ping` tool** — takes no parameters and returns `{"status": "pong"}`. Used to verify the server is reachable and responding correctly.
- **`python-dotenv` integration** — `load_dotenv()` is called at startup so environment variables from `.env` are available before any tool runs.

### File changes

| File | Change |
|------|--------|
| `src/server.py` | Full implementation of the MCP server |
| `phases/PHASE_1.md` | This documentation |

---

## How to Run the Server Locally

### Prerequisites

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env             # then set GITHUB_TOKEN in .env
```

### Start the server (stdio transport — default for MCP clients)

```bash
python src/server.py
```

The server listens on **stdio** by default, which is how MCP clients (e.g., Claude Desktop, Cursor) connect to it.

### Start with HTTP transport (useful for manual testing)

```bash
fastmcp run src/server.py --transport sse --port 8000
```

Then open `http://localhost:8000` to see the server info page.

---

## How to Test the Ping Tool

### Option 1: fastmcp dev inspector (recommended)

```bash
fastmcp dev src/server.py
```

This launches an interactive inspector in your browser. Click **ping** → **Run** and confirm the response is:

```json
{"status": "pong"}
```

### Option 2: Python test script

```python
import asyncio
from fastmcp import Client

async def test_ping():
    async with Client("src/server.py") as client:
        result = await client.call_tool("ping", {})
        print(result)   # expected: [TextContent(text='{"status": "pong"}')]

asyncio.run(test_ping())
```

### Option 3: Claude Desktop integration

Add the server to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "code-analyzer": {
      "command": "python",
      "args": ["/absolute/path/to/code-analyzer/src/server.py"]
    }
  }
}
```

Restart Claude Desktop and ask: _"Use the ping tool"_ — you should see `{"status": "pong"}` in the response.
