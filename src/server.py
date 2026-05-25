import asyncio
import json
import os
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastmcp import FastMCP
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

load_dotenv()

# Allow importing orchestrator from the same directory
sys.path.insert(0, str(Path(__file__).parent))

mcp = FastMCP("code-analyzer")

DEFAULT_OWNER = "manoj-github-avio"


# ── GitHub MCP helpers ────────────────────────────────────────────────────────

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


def _resolve_repo(repo: str) -> str:
    """Expand a bare repo name to owner/repo using the default owner."""
    return repo if "/" in repo else f"{DEFAULT_OWNER}/{repo}"


async def _find_latest_open_pr(session: ClientSession, owner: str, repo_name: str) -> int | None:
    """Return the PR number of the most recently opened open PR, or None."""
    data = await _call_tool(session, "list_pull_requests", {
        "owner": owner,
        "repo": repo_name,
        "state": "open",
    })
    if not data or not isinstance(data, list) or len(data) == 0:
        return None
    # list_pull_requests returns newest first
    return data[0]["number"]


# ── Existing server tools ─────────────────────────────────────────────────────

@mcp.tool()
def ping() -> dict:
    """Health-check tool. Returns a pong response to confirm the server is running."""
    return {"status": "pong"}


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
    repo = _resolve_repo(repo)
    owner, repo_name = repo.split("/", 1)

    async with stdio_client(_github_mcp_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

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


# ── New PR analysis tools ─────────────────────────────────────────────────────

async def _resolve_pr_number(session: ClientSession, owner: str, repo_name: str, pr_number: int | None) -> tuple[int, str]:
    """Return (pr_number, label). Auto-finds latest open PR if pr_number is None."""
    if pr_number is not None:
        return pr_number, f"PR #{pr_number}"
    found = await _find_latest_open_pr(session, owner, repo_name)
    if found is None:
        raise ValueError(f"No open pull requests found in {owner}/{repo_name}.")
    return found, f"latest open PR #{found}"


@mcp.tool()
async def run_pr_analyzer(repo: str, pr_number: int | None = None, design_doc_path: str | None = None) -> str:
    """Run full PR analysis including code summary, documentation audit and design alignment on a GitHub PR.
    Finds latest open PR automatically if pr_number not provided."""
    from orchestrator import (
        fetch_pr_diff, run_summarizer, run_auditor, run_alignment,
        format_report, post_pr_comment,
    )

    repo = _resolve_repo(repo)
    owner, repo_name = repo.split("/", 1)

    async with stdio_client(_github_mcp_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            pr_num, label = await _resolve_pr_number(session, owner, repo_name, pr_number)

    diff = await fetch_pr_diff(repo, pr_num)
    if not diff.strip():
        return f"Could not fetch diff for {repo} {label}."

    if design_doc_path:
        explanation, audit, alignment = await asyncio.gather(
            run_summarizer(diff), run_auditor(repo, diff), run_alignment(design_doc_path, diff),
        )
    else:
        explanation, audit = await asyncio.gather(run_summarizer(diff), run_auditor(repo, diff))
        alignment = None

    report = format_report(explanation, audit, alignment)
    await post_pr_comment(repo, pr_num, report)
    return report


@mcp.tool()
async def run_summarizer(repo: str, pr_number: int | None = None) -> str:
    """Summarize code changes in a GitHub PR in plain English.
    Finds latest open PR automatically if pr_number not provided."""
    from orchestrator import fetch_pr_diff, run_summarizer as _run_summarizer, format_summary_comment, post_pr_comment

    repo = _resolve_repo(repo)
    owner, repo_name = repo.split("/", 1)

    async with stdio_client(_github_mcp_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            pr_num, _ = await _resolve_pr_number(session, owner, repo_name, pr_number)

    diff = await fetch_pr_diff(repo, pr_num)
    if not diff.strip():
        return f"Could not fetch diff for {repo} PR #{pr_num}."

    explanation = await _run_summarizer(diff)
    comment = format_summary_comment(explanation)
    await post_pr_comment(repo, pr_num, comment)
    return comment


@mcp.tool()
async def run_documentation_auditor(repo: str, pr_number: int | None = None) -> str:
    """Audit documentation and README files against PR changes.
    Finds latest open PR automatically if pr_number not provided."""
    from orchestrator import fetch_pr_diff, run_auditor, format_audit_comment, post_pr_comment

    repo = _resolve_repo(repo)
    owner, repo_name = repo.split("/", 1)

    async with stdio_client(_github_mcp_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            pr_num, _ = await _resolve_pr_number(session, owner, repo_name, pr_number)

    diff = await fetch_pr_diff(repo, pr_num)
    if not diff.strip():
        return f"Could not fetch diff for {repo} PR #{pr_num}."

    audit = await run_auditor(repo, diff)
    comment = format_audit_comment(audit)
    if comment:
        await post_pr_comment(repo, pr_num, comment)
        return comment
    return "No documentation updates needed — no comment posted."


@mcp.tool()
async def run_design_alignment(repo: str, pr_number: int | None = None, design_doc_path: str | None = None) -> str:
    """Check if PR changes align with the solution design document.
    Finds latest open PR automatically if pr_number not provided."""
    from orchestrator import fetch_pr_diff, run_alignment, format_alignment_comment, post_pr_comment

    repo = _resolve_repo(repo)
    owner, repo_name = repo.split("/", 1)

    if not design_doc_path:
        return "design_doc_path is required for design alignment. Provide the path to a .docx, .md, .txt, or .pdf file."

    async with stdio_client(_github_mcp_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            pr_num, _ = await _resolve_pr_number(session, owner, repo_name, pr_number)

    diff = await fetch_pr_diff(repo, pr_num)
    if not diff.strip():
        return f"Could not fetch diff for {repo} PR #{pr_num}."

    alignment = await run_alignment(design_doc_path, diff)
    comment = format_alignment_comment(alignment)
    await post_pr_comment(repo, pr_num, comment)
    return comment


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
