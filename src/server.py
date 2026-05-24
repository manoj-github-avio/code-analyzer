import base64
import json
import os

import anthropic
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("code-analyzer")


@mcp.tool()
def ping() -> dict:
    """Health-check tool. Returns a pong response to confirm the server is running."""
    return {"status": "pong"}


@mcp.tool()
def get_markdown_files(repo: str, branch: str = "main") -> list:
    """Fetches all .md files from a GitHub repo. Returns [{filename, path, content}]."""
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    owner, repo_name = repo.split("/", 1)

    # Resolve branch to its tree SHA
    branch_resp = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo_name}/branches/{branch}",
        headers=headers,
    )
    branch_resp.raise_for_status()
    tree_sha = branch_resp.json()["commit"]["commit"]["tree"]["sha"]

    # Fetch the full recursive file tree
    tree_resp = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{tree_sha}",
        headers=headers,
        params={"recursive": "1"},
    )
    tree_resp.raise_for_status()

    md_files = [
        f for f in tree_resp.json().get("tree", [])
        if f["path"].endswith(".md") and f["type"] == "blob"
    ]

    results = []
    for file in md_files:
        blob_resp = httpx.get(
            f"https://api.github.com/repos/{owner}/{repo_name}/git/blobs/{file['sha']}",
            headers=headers,
        )
        if blob_resp.status_code != 200:
            continue
        content = base64.b64decode(blob_resp.json()["content"]).decode("utf-8")
        results.append({
            "filename": file["path"].split("/")[-1],
            "path": file["path"],
            "content": content,
        })

    return results


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
    return json.loads(response.content[0].text)


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
