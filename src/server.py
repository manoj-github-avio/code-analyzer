from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("code-analyzer")


@mcp.tool()
def ping() -> dict:
    """Health-check tool. Returns a pong response to confirm the server is running."""
    return {"status": "pong"}


if __name__ == "__main__":
    mcp.run()
