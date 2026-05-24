# Code Analyzer

A Python MCP (Model Context Protocol) server that analyzes GitHub pull requests across three
dimensions — code explanation, documentation drift, and design alignment — and posts a
structured report directly on the PR.

Built in 6 phases to demonstrate core Claude API and MCP concepts: tools, resources, prompt
caching, parallel async agents, and GitHub MCP server integration.

---

## Quick Start

```bash
git clone https://github.com/manoj-github-avio/code-analyzer.git
cd code-analyzer
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env          # fill in ANTHROPIC_API_KEY and GITHUB_PERSONAL_ACCESS_TOKEN
```

### Run the full PR analysis

```bash
python3 src/main.py manoj-github-avio/code-analyzer 5 design-doc-sample.docx
```

This fetches the PR diff, runs three analysis agents in parallel, and posts a markdown report
as a PR comment.

### Run individual agents

```bash
# Explain a PR diff in plain English
python3 src/explainer_agent.py sample-mule-pr.diff

# Audit README/docs for staleness
python3 src/readme_auditor_agent.py owner/repo sample-mule-pr.diff

# Check alignment with a design document
python3 src/design_alignment_agent.py owner/repo sample-mule-pr.diff design-doc-sample.docx
```

---

## Architecture

```
src/main.py
  └── src/orchestrator.py
        ├── fetch_pr_diff()           GitHub MCP → get_pull_request_files
        │
        ├── asyncio.gather()          ← runs all three in parallel
        │     ├── run_explainer()     Anthropic API + MuleSoft skill (prompt cached)
        │     ├── run_auditor()       GitHub MCP → search_code / get_file_contents
        │     │                       + Anthropic API
        │     └── run_alignment()     local file read (.docx/.md/.txt/.pdf)
        │                             + Anthropic API
        │
        ├── format_report()           markdown aggregation
        └── post_pr_comment()         GitHub MCP → add_issue_comment
```

### MCP server tools (src/server.py)

Claude Desktop can use these tools directly:

| Tool | Description |
|------|-------------|
| `ping` | Health check |
| `get_markdown_files(repo, branch)` | Fetch all `.md` files via GitHub MCP server |
| `audit_markdown_files(diff, content)` | Audit docs against a diff |
| `read_design_doc(file_path)` | Read `.docx`, `.md`, `.txt`, or `.pdf` |

### MCP resource (src/server.py)

```
design-doc://local/{path}    →  exposes any local design doc as an MCP resource
```

---

## Project Phases

| Phase | What was built | Key concept |
|-------|---------------|-------------|
| [Phase 1](phases/PHASE_1.md) | MCP server skeleton + `ping` tool | FastMCP, stdio transport |
| [Phase 2](phases/PHASE_2.md) | GitHub MCP server integration in Claude Desktop | MCP server composition |
| [Phase 3](phases/PHASE_3.md) | MuleSoft PR explainer CLI + Claude Skill format | Prompt caching, skills |
| [Phase 4](phases/PHASE_4.md) | README auditor + GitHub MCP client from Python | MCP client SDK, async tools |
| [Phase 5](phases/PHASE_5.md) | Design alignment agent + `.docx` support | MCP resources, python-docx |
| [Phase 6](phases/PHASE_6.md) | Parallel orchestrator + PR comment posting | `asyncio.gather`, AsyncAnthropic |

---

## Requirements

- Python 3.11+
- Node.js (for `npx @modelcontextprotocol/server-github`)
- `ANTHROPIC_API_KEY` — from [console.anthropic.com](https://console.anthropic.com/settings/keys)
- `GITHUB_PERSONAL_ACCESS_TOKEN` — scopes: `repo` (or `public_repo`)

---

## Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "code-analyzer": {
      "command": "/path/to/python3",
      "args": ["/path/to/code-analyzer/src/server.py"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..." }
    }
  }
}
```
