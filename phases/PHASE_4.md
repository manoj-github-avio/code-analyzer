# Phase 4: README Auditor Agent

## What Was Implemented

Two new MCP tools added to `src/server.py` that let Claude Desktop check whether a PR's
documentation is in sync with its code changes.

A standalone CLI agent (`src/readme_auditor_agent.py`) that fetches all markdown files from
a GitHub repo, sends them with a PR diff to Claude, and prints a structured audit report.

---

## Tools Added to src/server.py

### `get_markdown_files(repo, branch="main")`

Fetches every `.md` file in a GitHub repository.

| Step | What it does |
|------|-------------|
| 1 | Resolves the branch name to its git tree SHA via the GitHub Branches API. |
| 2 | Fetches the full recursive file tree (`/git/trees/{sha}?recursive=1`). |
| 3 | Filters to `.md` blob entries. |
| 4 | Fetches each file's raw content via the Blobs API and base64-decodes it. |

Returns: `[{"filename": "README.md", "path": "docs/README.md", "content": "..."}]`

Requires `GITHUB_TOKEN` in `.env`.

### `audit_markdown_files(diff, markdown_files_content)`

Sends a PR diff and serialized markdown file list to Claude and returns a structured audit.

Returns:
```json
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
```

- `status` is always `"needs_update"` or `"up_to_date"`.
- Every markdown file appears in the list, even files that need no changes.
- Uses `claude-sonnet-4-6` with a structured JSON system prompt.

---

## CLI Agent: src/readme_auditor_agent.py

The agent combines both operations into a single command.

### How to run

```bash
# With a diff file
python src/readme_auditor_agent.py owner/repo my-pr.diff

# With a piped diff
git diff HEAD~1 HEAD | python src/readme_auditor_agent.py owner/repo

# Using the sample MuleSoft diff
python src/readme_auditor_agent.py owner/repo sample-mule-pr.diff
```

### Prerequisites

```bash
pip install -e .
# .env must have both keys:
# GITHUB_TOKEN=...
# ANTHROPIC_API_KEY=...
```

### Example output

```
Fetching markdown files from owner/my-repo...
Found 3 markdown file(s). Auditing...

=== README Audit Results ===
Summary: 2 of 3 files need updates

Files that need updates:
  [UPDATE] README.md — API Endpoints
           Add the new /health endpoint that returns version and uptime.
  [UPDATE] CHANGELOG.md — Unreleased
           Add an entry describing the Salesforce integration and multi-currency support.

Files that are up to date:
  [OK]     CONTRIBUTING.md
```

---

## Files Added / Modified

| File | Change |
|------|--------|
| `src/server.py` | Added `get_markdown_files` and `audit_markdown_files` MCP tools |
| `src/readme_auditor_agent.py` | New CLI agent |
| `sample-readme-audit.json` | Example showing diff, markdown input, and expected audit output |

---

## Architecture Notes

- **GitHub Blobs API** — fetching file content via blob SHA avoids making a separate
  `/contents/{path}` call per file; one tree fetch + N blob fetches.
- **Structured JSON output** — the system prompt instructs Claude to return raw JSON only,
  no markdown fences. The response is parsed directly with `json.loads()`.
- **MCP tools mirror CLI logic** — `server.py` exposes the same operations as MCP tools
  for Claude Desktop; `readme_auditor_agent.py` implements the same logic standalone for
  direct CLI use.
