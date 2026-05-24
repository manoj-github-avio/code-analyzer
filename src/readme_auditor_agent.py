"""
Audit markdown documentation files in a GitHub repo against a PR diff.

Usage:
    python src/readme_auditor_agent.py <owner/repo> <diff-file>
    cat my.diff | python src/readme_auditor_agent.py <owner/repo>

Example:
    python src/readme_auditor_agent.py owner/my-repo sample-mule-pr.diff
"""

import base64
import json
import os
import sys
from pathlib import Path

import anthropic
import httpx
from dotenv import load_dotenv

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


def get_markdown_files(repo: str, branch: str = "main") -> list[dict]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    owner, repo_name = repo.split("/", 1)

    branch_resp = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo_name}/branches/{branch}",
        headers=headers,
    )
    branch_resp.raise_for_status()
    tree_sha = branch_resp.json()["commit"]["commit"]["tree"]["sha"]

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
    return json.loads(response.content[0].text)


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


def main():
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
    files = get_markdown_files(repo)
    print(f"Found {len(files)} markdown file(s). Auditing...", file=sys.stderr)

    results = audit_markdown_files(diff, files)
    display_results(results)


if __name__ == "__main__":
    main()
