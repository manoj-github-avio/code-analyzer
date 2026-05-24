import json
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastmcp import FastMCP
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

load_dotenv()

mcp = FastMCP("code-analyzer")


@mcp.tool()
def ping() -> dict:
    """Health-check tool. Returns a pong response to confirm the server is running."""
    return {"status": "pong"}


def _github_mcp_params() -> StdioServerParameters:
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN", "")
    return StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": token},
    )


async def _call_tool(session: ClientSession, name: str, args: dict):
    result = await session.call_tool(name, args)
    if result.isError or not result.content:
        return None
    return json.loads(result.content[0].text)


async def _fetch_md_from_dir(session: ClientSession, owner: str, repo_name: str, path: str, branch: str) -> list:
    """Lists a directory and returns [{filename, path, content}] for every .md file found."""
    listing = await _call_tool(session, "get_file_contents", {
        "owner": owner, "repo": repo_name, "path": path, "branch": branch,
    })
    if not isinstance(listing, list):
        return []

    results = []
    for item in listing:
        if item.get("type") == "file" and item["name"].endswith(".md"):
            file_data = await _call_tool(session, "get_file_contents", {
                "owner": owner, "repo": repo_name, "path": item["path"], "branch": branch,
            })
            if file_data and isinstance(file_data, dict):
                results.append({
                    "filename": item["name"],
                    "path": item["path"],
                    "content": file_data.get("content", ""),
                })
    return results


@mcp.tool()
async def get_markdown_files(repo: str, branch: str = "main") -> list:
    """Fetches all .md files from a GitHub repo using the GitHub MCP server. Returns [{filename, path, content}]."""
    owner, repo_name = repo.split("/", 1)

    async with stdio_client(_github_mcp_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Primary: use code search to discover .md files across the whole repo
            search_data = await _call_tool(session, "search_code", {
                "q": f"repo:{owner}/{repo_name} extension:md",
            })
            items = search_data.get("items", []) if search_data else []

            if items:
                results = []
                for item in items:
                    file_data = await _call_tool(session, "get_file_contents", {
                        "owner": owner, "repo": repo_name,
                        "path": item["path"], "branch": branch,
                    })
                    if file_data and isinstance(file_data, dict):
                        results.append({
                            "filename": item["name"],
                            "path": item["path"],
                            "content": file_data.get("content", ""),
                        })
                return results

            # Fallback: scan root directory directly (handles repos not yet indexed by GitHub search)
            return await _fetch_md_from_dir(session, owner, repo_name, "", branch)


_AUDIT_SYSTEM = """You are a technical writer auditing markdown documentation against a code PR diff.

Identify which documentation files and sections need updating based on the code changes.

Return ONLY valid JSON — no other text, no markdown fences:
{
  "files_to_update": [
    {
      "file": "README.md",
      "section": "API Endpoints",
      "status": "needs_update",
      "suggestion": "Add the new /health endpoint introduced in this PR."
    },
    {
      "file": "CONTRIBUTING.md",
      "section": "Setup",
      "status": "up_to_date"
    }
  ],
  "summary": "1 of 2 files needs updates"
}

Rules:
- Include every markdown file in the list, even files that are up_to_date.
- status must be exactly "needs_update" or "up_to_date".
- Only suggest concrete, actionable changes tied to what changed in the diff.
- summary must state how many files need updates out of the total.
"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


@mcp.tool()
def audit_markdown_files(diff: str, markdown_files_content: str) -> dict:
    """Audits markdown files against a PR diff. Returns structured update suggestions."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_AUDIT_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"PR diff:\n```diff\n{diff}\n```\n\n"
                    f"Markdown files:\n{markdown_files_content}"
                ),
            }
        ],
    )
    return _parse_json(response.content[0].text)


# ── Design Alignment Tools ────────────────────────────────────────────────────

def _read_design_doc(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Design document not found: {file_path}")
    suffix = path.suffix.lower()
    if suffix in (".md", ".txt"):
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        from docx import Document
        doc = Document(str(path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(p.extract_text() for p in reader.pages if p.extract_text())
    raise ValueError(f"Unsupported format '{suffix}'. Supported: .md, .txt, .docx, .pdf")


@mcp.tool()
def read_design_doc(file_path: str) -> str:
    """Reads a local design document (.md, .txt, .docx, .pdf) and returns its plain-text content."""
    return _read_design_doc(file_path)


@mcp.resource("design-doc://local/{path}")
def design_doc_resource(path: str) -> str:
    """Exposes a local design document as an MCP resource. URI: design-doc://local/{path}"""
    return _read_design_doc(path)


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
