"""
Shared async agent logic for the code-analyzer CLI.

Imported by src/cli.py. Functions:
    fetch_pr_diff()    — fetch a unified diff from GitHub via MCP
    run_explainer()    — plain-English PR summary (AsyncAnthropic, prompt cached)
    run_auditor()      — markdown doc audit (GitHub MCP + AsyncAnthropic)
    run_alignment()    — design doc alignment check (AsyncAnthropic)
    format_report()    — aggregate results into a markdown PR comment
    post_pr_comment()  — post the report to GitHub via MCP
"""

import asyncio
import json
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

load_dotenv()

SKILLS_DIR = Path(__file__).parent.parent / "skills"


# ── GitHub MCP helpers ──────────────────────────────────────────────────────

def _github_mcp_params() -> StdioServerParameters:
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN", "")
    return StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": token},
    )


async def _github_call(session: ClientSession, name: str, args: dict):
    result = await session.call_tool(name, args)
    if result.isError or not result.content:
        return None
    return json.loads(result.content[0].text)


# ── Shared utilities ────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


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


# ── Step 1: Fetch PR diff ───────────────────────────────────────────────────

async def fetch_pr_diff(repo: str, pr_number: int) -> str:
    """Fetch the unified diff for a PR using the GitHub MCP server."""
    owner, repo_name = repo.split("/", 1)
    async with stdio_client(_github_mcp_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            files = await _github_call(session, "get_pull_request_files", {
                "owner": owner, "repo": repo_name, "pull_number": pr_number,
            })

    if not isinstance(files, list):
        return ""
    parts = []
    for f in files:
        parts.append(f"diff --git a/{f['filename']} b/{f['filename']}")
        if f.get("patch"):
            parts.append(f["patch"])
    return "\n".join(parts)


# ── Step 2a: Code Explainer ─────────────────────────────────────────────────

_EXPLAINER_SYSTEM = """\
You are an expert MuleSoft integration engineer who excels at explaining technical changes \
to non-technical stakeholders.

Read a MuleSoft PR diff and produce a clear, plain-English explanation useful to:
1. Developers unfamiliar with MuleSoft.
2. Non-technical readers (business analysts, QA, product owners).

Structure your explanation as:

## Summary
One or two sentences. What does this change do?

## What changed
Bullet list of specific modifications — flows, connectors, DataWeave, error handling.

## Systems involved
Which external systems are touched? Any new dependencies introduced?

## Error handling
What happens when something goes wrong?

## Impact assessment
Is this breaking? Who should be notified or needs to test this?

Use plain sentences. Avoid XML snippets. Define MuleSoft terms on first mention."""


async def run_explainer(diff: str) -> str:
    skill_path = SKILLS_DIR / "mulesoft" / "SKILL.md"
    mulesoft_knowledge = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

    system_blocks = []
    if mulesoft_knowledge:
        system_blocks.append({
            "type": "text",
            "text": mulesoft_knowledge,
            "cache_control": {"type": "ephemeral"},
        })
    system_blocks.append({
        "type": "text",
        "text": _EXPLAINER_SYSTEM,
        "cache_control": {"type": "ephemeral"},
    })

    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_blocks,
        messages=[{
            "role": "user",
            "content": f"Please explain the following MuleSoft PR diff:\n\n```diff\n{diff}\n```",
        }],
    )
    return response.content[0].text


# ── Step 2b: README Auditor ─────────────────────────────────────────────────

_AUDIT_SYSTEM = """\
You are a technical writer auditing markdown documentation against a code PR diff.

Return ONLY valid JSON — no markdown fences:
{
  "files_to_update": [
    {"file": "README.md", "section": "API Endpoints", "status": "needs_update", "suggestion": "..."},
    {"file": "CONTRIBUTING.md", "section": "Setup", "status": "up_to_date"}
  ],
  "summary": "1 of 2 files needs updates"
}

status must be "needs_update" or "up_to_date". Include every markdown file."""


async def _fetch_md_files(session: ClientSession, owner: str, repo_name: str) -> list:
    search_data = await _github_call(session, "search_code", {
        "q": f"repo:{owner}/{repo_name} extension:md",
    })
    items = search_data.get("items", []) if search_data else []

    if items:
        results = []
        for item in items:
            file_data = await _github_call(session, "get_file_contents", {
                "owner": owner, "repo": repo_name, "path": item["path"],
            })
            if file_data and isinstance(file_data, dict):
                results.append({
                    "filename": item["name"],
                    "path": item["path"],
                    "content": file_data.get("content", ""),
                })
        return results

    # Fallback: scan root directory
    listing = await _github_call(session, "get_file_contents", {
        "owner": owner, "repo": repo_name, "path": "",
    })
    if not isinstance(listing, list):
        return []
    results = []
    for item in listing:
        if item.get("type") == "file" and item["name"].endswith(".md"):
            file_data = await _github_call(session, "get_file_contents", {
                "owner": owner, "repo": repo_name, "path": item["path"],
            })
            if file_data and isinstance(file_data, dict):
                results.append({
                    "filename": item["name"],
                    "path": item["path"],
                    "content": file_data.get("content", ""),
                })
    return results


async def run_auditor(repo: str, diff: str) -> dict:
    owner, repo_name = repo.split("/", 1)
    async with stdio_client(_github_mcp_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            files = await _fetch_md_files(session, owner, repo_name)

    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_AUDIT_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"PR diff:\n```diff\n{diff}\n```\n\n"
                f"Markdown files:\n{json.dumps(files, indent=2)}"
            ),
        }],
    )
    return _parse_json(response.content[0].text)


# ── Step 2c: Design Alignment ───────────────────────────────────────────────

_ALIGNMENT_SYSTEM = """\
You are a software architect reviewing a PR diff for alignment with a design document.

Return ONLY valid JSON — no markdown fences:
{
  "drifts": [
    {"area": "Error Handling", "issue": "...", "severity": "high", "suggestion": "..."}
  ],
  "aligned": ["Correlation ID captured from inbound request as required by design section 3"],
  "summary": "2 drift(s) detected, 3 areas aligned"
}

severity must be "high", "medium", or "low"."""


async def run_alignment(design_doc_path: str, diff: str) -> dict:
    design_doc = await asyncio.to_thread(_read_design_doc, design_doc_path)
    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=_ALIGNMENT_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Design document:\n\n{design_doc}\n\n---\n\n"
                f"PR diff:\n```diff\n{diff}\n```"
            ),
        }],
    )
    return _parse_json(response.content[0].text)


# ── Step 3: Format report ───────────────────────────────────────────────────

def format_report(repo: str, pr_number: int, explanation: str, audit: dict, alignment: dict) -> str:
    lines = [
        "## 🤖 Code Analyzer Report",
        "",
        f"**Repository:** `{repo}` &nbsp;|&nbsp; **PR:** #{pr_number}",
        "",
        "---",
        "",
        "## 📝 Code Summary",
        "",
        explanation.strip(),
        "",
        "---",
        "",
        "## 📚 README Updates Needed",
        "",
        f"**{audit.get('summary', 'No markdown files found')}**",
        "",
    ]

    files = audit.get("files_to_update", [])
    needs_update = [f for f in files if f.get("status") == "needs_update"]
    up_to_date = [f for f in files if f.get("status") == "up_to_date"]

    if needs_update:
        lines += ["| File | Section | Suggested update |",
                  "|------|---------|------------------|"]
        for f in needs_update:
            lines.append(f"| `{f['file']}` | {f.get('section', '—')} | {f.get('suggestion', '—')} |")
        lines.append("")

    if up_to_date:
        names = ", ".join(f"`{f['file']}`" for f in up_to_date)
        lines += [f"**Up to date:** {names}", ""]

    drifts = alignment.get("drifts", [])
    aligned = alignment.get("aligned", [])

    lines += [
        "---",
        "",
        "## 🏗️ Design Alignment",
        "",
        f"**{alignment.get('summary', '')}**",
        "",
    ]

    if drifts:
        lines += ["### ❌ Drift Issues", ""]
        for d in drifts:
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(d.get("severity", "medium"), "🟡")
            lines += [
                f"**{emoji} [{d.get('severity', 'medium').upper()}] {d['area']}**",
                f"- **Issue:** {d['issue']}",
            ]
            if d.get("suggestion"):
                lines.append(f"- **Fix:** {d['suggestion']}")
            lines.append("")

    if aligned:
        lines += ["### ✅ Aligned with Design", ""]
        for a in aligned:
            lines.append(f"- {a}")
        lines.append("")

    lines += [
        "---",
        "",
        "*Generated by [code-analyzer](https://github.com/manoj-github-avio/code-analyzer) "
        "— powered by Claude claude-sonnet-4-6*",
    ]

    return "\n".join(lines)


# ── Step 4: Post PR comment ─────────────────────────────────────────────────

async def post_pr_comment(repo: str, pr_number: int, body: str) -> None:
    owner, repo_name = repo.split("/", 1)
    async with stdio_client(_github_mcp_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await _github_call(session, "add_issue_comment", {
                "owner": owner,
                "repo": repo_name,
                "issue_number": pr_number,
                "body": body,
            })


