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

### From the terminal (CLI)

After `pip install -e .`, the `code-analyzer` command is available anywhere in the virtualenv:

```bash
# Full analysis — fetch diff, run all agents, post PR comment:
code-analyzer orchestrator manoj-github-avio/code-analyzer 5 samples/design-doc-sample.docx
code-analyzer orchestrator manoj-github-avio/code-analyzer 5 --no-post   # preview without posting

# Test mode — local diff file, no GitHub PR needed:
code-analyzer orchestrator manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx

# Run agents individually:
code-analyzer explainer manoj-github-avio/code-analyzer 5
code-analyzer explainer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff

code-analyzer auditor manoj-github-avio/code-analyzer 5
code-analyzer auditor manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff

code-analyzer designer manoj-github-avio/code-analyzer 5 samples/design-doc-sample.docx
code-analyzer designer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx

# Help:
code-analyzer --help
code-analyzer explainer --help
```

### From Claude Code (slash commands)

Four slash commands are defined in `.claude/commands/` and available inside any Claude Code
session opened in this project:

```
/explainer    manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
/auditor      manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
/designer     manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
/orchestrator manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
```

Each slash command tells Claude to run the corresponding `code-analyzer` CLI subcommand
and show the output.

---

## Architecture

```
Two entry points — same underlying logic:

.claude/commands/*.md    ← /slash commands in Claude Code
        │                   each tells Claude to run: code-analyzer <subcommand> ...
        ▼
src/cli.py               ← Click CLI, registered as 'code-analyzer' console script
src/main.py              ← thin wrapper (python3 src/main.py → orchestrator subcommand)
        │
        └── src/orchestrator.py          ← all async agent logic
              ├── fetch_pr_diff()        GitHub MCP → get_pull_request_files
              ├── run_explainer()        Anthropic API + MuleSoft skill (prompt cached)
              ├── run_auditor()          GitHub MCP + Anthropic API
              ├── run_alignment()        local file read + Anthropic API
              ├── format_report()        markdown aggregation
              └── post_pr_comment()     GitHub MCP → add_issue_comment
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
