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
# Via the code-analyzer CLI (registered by pip install -e .):
code-analyzer orchestrator manoj-github-avio/code-analyzer 5 design-doc-sample.docx
code-analyzer orchestrator manoj-github-avio/code-analyzer --test sample-mule-pr.diff design-doc-sample.docx
code-analyzer orchestrator manoj-github-avio/code-analyzer 5 --no-post   # preview without posting

# Via python module (no install needed):
python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff
```

### Run agents individually

Each agent is a standalone CLI subcommand with `--help` and `--test` support:

```bash
# Explain a PR diff in plain English
code-analyzer explainer manoj-github-avio/code-analyzer 5
code-analyzer explainer manoj-github-avio/code-analyzer --test sample-mule-pr.diff

# Audit README/docs for staleness
code-analyzer auditor manoj-github-avio/code-analyzer 5
code-analyzer auditor manoj-github-avio/code-analyzer --test sample-mule-pr.diff

# Check alignment with a design document
code-analyzer designer manoj-github-avio/code-analyzer 5 design-doc-sample.docx
code-analyzer designer manoj-github-avio/code-analyzer --test sample-mule-pr.diff design-doc-sample.docx

# Help:
code-analyzer --help
code-analyzer explainer --help
```

### Claude Code slash commands

When working in this project in Claude Code, four slash commands are available:

```
/explainer manoj-github-avio/code-analyzer --test sample-mule-pr.diff
/auditor   manoj-github-avio/code-analyzer --test sample-mule-pr.diff
/designer  manoj-github-avio/code-analyzer --test sample-mule-pr.diff design-doc-sample.docx
/orchestrator manoj-github-avio/code-analyzer --test sample-mule-pr.diff design-doc-sample.docx
```

These are defined in `.claude/commands/` and tell Claude to run the corresponding
`code-analyzer` CLI subcommand and display the output.

---

## Architecture

```
.claude/commands/*.md          ← Claude Code /slash commands
  └── code-analyzer CLI        ← registered console script (pip install -e .)
        └── src/cli.py         ← Click entry point, four subcommands
              │
src/main.py ──┤
              └── src/commands/orchestrator_command.py  ← argparse, --test / --no-post
                    │
                    └── src/orchestrator.py             ← shared async business logic
                          ├── fetch_pr_diff()           GitHub MCP → get_pull_request_files
                          │
                          ├── asyncio.gather()          ← runs all three in parallel
                          │     ├── run_explainer()     Anthropic API + MuleSoft skill (cached)
                          │     ├── run_auditor()       GitHub MCP → search_code / get_file_contents
                          │     └── run_alignment()     local file read + Anthropic API
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
