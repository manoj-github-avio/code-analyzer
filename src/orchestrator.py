"""
Shared async agent logic for the code-analyzer CLI.

Imported by src/cli.py. Functions:
    fetch_pr_diff()    — fetch a unified diff from GitHub via MCP
    run_summarizer()   — plain-English PR summary (AsyncAnthropic, prompt cached)
    run_auditor()      — markdown doc audit (GitHub MCP + AsyncAnthropic, prompt cached)
    run_alignment()    — design doc alignment check (AsyncAnthropic, prompt cached)
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


# ── Step 2a: Summarizer Agent ────────────────────────────────────────────────

_SUMMARIZER_SYSTEM = """\
You are an expert MuleSoft integration engineer.

Read a MuleSoft PR diff and produce a concise, factual explanation for developers and \
non-technical readers.

Structure your output as:

## Summary
A factual description of what this change does. Be as detailed as needed — no artificial limits.

## What Changed
3 to 5 bullet points. Each bullet is one major change, described in 1-2 sentences maximum.
Focus on WHAT changed, not HOW. No file-by-file breakdowns, no subsections, no nested bullets.
Example format:
- New POST endpoint added for student application submissions
- New implementation sub-flow added for processing student applications
- Postman environment file added for production testing

Use plain sentences. Define MuleSoft terms on first mention.
Do not include assumptions, guesses, or suggestions about intent."""


async def run_summarizer(diff: str) -> str:
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
        "text": _SUMMARIZER_SYSTEM,
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


# ── Step 2b: Documentation Auditor Agent ────────────────────────────────────

_AUDIT_SYSTEM = """\
You are a technical writer auditing markdown documentation against a code PR diff.

Return ONLY valid JSON — no markdown fences:
{
  "files_to_update": [
    {
      "file": "README.md",
      "status": "needs_update",
      "suggestion": "- Update API endpoint descriptions\\n- Add new Postman environment file to setup section"
    }
  ],
  "summary": "1 of 1 files needs updates"
}

Rules:
- Only include files with status "needs_update" — omit files that are up to date.
- suggestion must be a markdown bullet list (each item starts with "- ").
- No code examples, no endpoint paths, no JSON snippets in suggestions.
- Keep suggestions brief and plain: describe what to update, not how.
- Only include actionable changes tied to what actually changed in the diff.
- summary must state how many files need updates out of total markdown files found."""


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
        system=[{
            "type": "text",
            "text": _AUDIT_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
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
    {"area": "Error Handling", "issue": "...", "severity": "high"}
  ],
  "summary": "2 issue(s) detected"
}

Rules:
- Only include drifts with severity "high" or "medium" — omit low severity issues.
- Do NOT include an "aligned" list.
- Do NOT include fix suggestions — only state the issue.
- severity must be "high" or "medium".
- high: directly contradicts an explicit design decision or introduces an out-of-scope feature.
- medium: deviates from a recommended pattern but does not break a hard rule."""


async def run_alignment(design_doc_path: str, diff: str) -> dict:
    design_doc = await asyncio.to_thread(_read_design_doc, design_doc_path)
    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=[{
            "type": "text",
            "text": _ALIGNMENT_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Design document:\n\n{design_doc}",
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": f"\n\n---\n\nPR diff:\n```diff\n{diff}\n```",
                },
            ],
        }],
    )
    return _parse_json(response.content[0].text)


# ── Step 3: Format sections & report ────────────────────────────────────────

_FOOTER = (
    "---\n\n*Generated by [code-analyzer](https://github.com/manoj-github-avio/code-analyzer) "
    "— powered by Claude claude-sonnet-4-6*"
)


def _strip_summary_heading(text: str) -> str:
    text = text.strip()
    if text.startswith("## Summary"):
        text = text[len("## Summary"):].lstrip("\n")
    return text


def _alignment_lines(alignment: dict) -> list[str]:
    drifts = alignment.get("drifts", [])
    lines = ["## 🏗️ Design Alignment", "", f"**{alignment.get('summary', '')}**", ""]
    if drifts:
        for d in drifts:
            emoji = {"high": "🔴", "medium": "🟡"}.get(d.get("severity", "medium"), "🟡")
            lines.append(f"- {emoji} **[{d.get('severity', 'medium').upper()}] {d['area']}:** {d['issue']}")
        lines.append("")
    else:
        lines += ["No drift issues detected.", ""]
    return lines


def format_summary_comment(explanation: str) -> str:
    """Standalone PR comment for the Summarizer Agent."""
    return f"## 📝 Summary\n\n{_strip_summary_heading(explanation)}\n\n{_FOOTER}"


def format_audit_comment(audit: dict) -> str:
    """Standalone PR comment for the Documentation Auditor Agent. Returns '' if nothing to update."""
    needs_update = [f for f in audit.get("files_to_update", []) if f.get("status") == "needs_update"]
    if not needs_update:
        return ""
    lines = ["## 📚 Documentation Updates Needed", "", f"**{audit.get('summary', '')}**", ""]
    for f in needs_update:
        lines += [f"**`{f['file']}`**", f.get("suggestion", "").strip(), ""]
    return "\n".join(lines) + f"\n\n{_FOOTER}"


def format_alignment_comment(alignment: dict) -> str:
    """Standalone PR comment for the Design Alignment Agent."""
    return "\n".join(_alignment_lines(alignment)) + f"\n\n{_FOOTER}"


def format_report(explanation: str, audit: dict, alignment: dict | None = None) -> str:
    """Combined orchestrator report. Omits sections with no content."""
    parts = [
        "## 🤖 Code Analyzer Report",
        "",
        "---",
        "",
        "## 📝 Summary",
        "",
        _strip_summary_heading(explanation),
    ]

    needs_update = [f for f in audit.get("files_to_update", []) if f.get("status") == "needs_update"]
    if needs_update:
        parts += ["", "---", "", "## 📚 Documentation Updates Needed", "", f"**{audit.get('summary', '')}**", ""]
        for f in needs_update:
            parts += [f"**`{f['file']}`**", f.get("suggestion", "").strip(), ""]

    if alignment is not None:
        parts += ["", "---", ""] + _alignment_lines(alignment)

    parts += ["", "---", "", "*Generated by [code-analyzer](https://github.com/manoj-github-avio/code-analyzer) — powered by Claude claude-sonnet-4-6*"]
    return "\n".join(parts)


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


