"""
Audit markdown documentation files in a GitHub repo against a PR diff.

Usage:
    python src/readme_auditor_agent.py <owner/repo> <diff-file>
    cat my.diff | python src/readme_auditor_agent.py <owner/repo>

Example:
    python src/readme_auditor_agent.py owner/my-repo samples/sample-mule-pr.diff
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

load_dotenv()

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


async def get_markdown_files(repo: str, branch: str | None = None) -> list[dict]:
    """Fetch all .md files from a GitHub repo using the GitHub MCP server."""
    owner, repo_name = repo.split("/", 1)

    async with stdio_client(_github_mcp_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Primary: code search finds .md files across the whole repo
            search_data = await _call_tool(session, "search_code", {
                "q": f"repo:{owner}/{repo_name} extension:md",
            })
            items = search_data.get("items", []) if search_data else []

            if items:
                results = []
                for item in items:
                    args = {"owner": owner, "repo": repo_name, "path": item["path"]}
                    if branch:
                        args["branch"] = branch
                    file_data = await _call_tool(session, "get_file_contents", args)
                    if file_data and isinstance(file_data, dict):
                        results.append({
                            "filename": item["name"],
                            "path": item["path"],
                            "content": file_data.get("content", ""),
                        })
                return results

            # Fallback: scan root directory (handles repos not yet indexed by GitHub search)
            dir_args = {"owner": owner, "repo": repo_name, "path": ""}
            if branch:
                dir_args["branch"] = branch
            listing = await _call_tool(session, "get_file_contents", dir_args)
            if not isinstance(listing, list):
                return []

            results = []
            for item in listing:
                if item.get("type") == "file" and item["name"].endswith(".md"):
                    args = {"owner": owner, "repo": repo_name, "path": item["path"]}
                    if branch:
                        args["branch"] = branch
                    file_data = await _call_tool(session, "get_file_contents", args)
                    if file_data and isinstance(file_data, dict):
                        results.append({
                            "filename": item["name"],
                            "path": item["path"],
                            "content": file_data.get("content", ""),
                        })
            return results


def _parse_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def audit_markdown_files(diff: str, files: list[dict]) -> dict:
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
                    f"Markdown files:\n{json.dumps(files, indent=2)}"
                ),
            }
        ],
    )
    return _parse_json(response.content[0].text)


def read_diff() -> str:
    if len(sys.argv) > 2:
        diff_path = Path(sys.argv[2])
        if not diff_path.exists():
            print(f"Error: file not found: {diff_path}", file=sys.stderr)
            sys.exit(1)
        return diff_path.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Usage: python src/readme_auditor_agent.py <owner/repo> [diff-file]", file=sys.stderr)
    sys.exit(1)


def display_results(results: dict) -> None:
    files = results.get("files_to_update", [])
    needs_update = [f for f in files if f.get("status") == "needs_update"]
    up_to_date = [f for f in files if f.get("status") == "up_to_date"]

    print(f"\n=== README Audit Results ===")
    print(f"Summary: {results.get('summary', '')}\n")

    if needs_update:
        print("Files that need updates:")
        for item in needs_update:
            section = item.get("section", "General")
            print(f"  [UPDATE] {item['file']} — {section}")
            if suggestion := item.get("suggestion"):
                print(f"           {suggestion}")

    if up_to_date:
        print("\nFiles that are up to date:")
        for item in up_to_date:
            print(f"  [OK]     {item['file']}")

    print()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python src/readme_auditor_agent.py <owner/repo> [diff-file]", file=sys.stderr)
        print("       cat my.diff | python src/readme_auditor_agent.py <owner/repo>", file=sys.stderr)
        sys.exit(1)

    repo = sys.argv[1]
    diff = read_diff()

    if not diff.strip():
        print("Error: diff is empty.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching markdown files from {repo}...", file=sys.stderr)
    files = await get_markdown_files(repo)
    print(f"Found {len(files)} markdown file(s). Auditing...", file=sys.stderr)

    results = audit_markdown_files(diff, files)
    display_results(results)


if __name__ == "__main__":
    asyncio.run(main())
