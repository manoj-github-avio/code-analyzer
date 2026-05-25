# Code Analyzer

A Python MCP (Model Context Protocol) server that analyzes GitHub pull requests across three
dimensions — code summarization, documentation drift, and design alignment — and posts a
structured report directly on the PR.

Demonstrates core Claude API and MCP concepts: tools, resources, prompt caching, parallel
async agents, and GitHub MCP server integration.

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
# Orchestrator — run all agents, post combined PR comment:
code-analyzer orchestrator manoj-github-avio/student-api 1
code-analyzer orchestrator manoj-github-avio/student-api 1 path/to/sdd.docx   # with design doc
code-analyzer orchestrator manoj-github-avio/student-api 1 --no-post          # preview without posting

# Test mode — local diff file, no GitHub PR needed:
code-analyzer orchestrator manoj-github-avio/student-api --test samples/sample-mule-pr.diff
code-analyzer orchestrator manoj-github-avio/student-api --test samples/sample-mule-pr.diff samples/design-doc-sample.docx

# Individual agents — each posts its own PR comment:
code-analyzer summarizer manoj-github-avio/student-api 1
code-analyzer documentation-auditor manoj-github-avio/student-api 1
code-analyzer designer manoj-github-avio/student-api 1 path/to/sdd.docx

# Preview individual agents without posting:
code-analyzer summarizer manoj-github-avio/student-api 1 --no-post
code-analyzer documentation-auditor manoj-github-avio/student-api 1 --no-post

# Test mode for individual agents:
code-analyzer summarizer manoj-github-avio/student-api --test samples/sample-mule-pr.diff
code-analyzer documentation-auditor manoj-github-avio/student-api --test samples/sample-mule-pr.diff
code-analyzer designer manoj-github-avio/student-api --test samples/sample-mule-pr.diff samples/design-doc-sample.docx

# Help:
code-analyzer --help
code-analyzer summarizer --help
code-analyzer orchestrator --help
```

### From Claude Code (slash commands)

Five slash commands are defined in `.claude/commands/` and available inside any Claude Code
session opened in this project:

```
/summarizer            manoj-github-avio/student-api 1
/documentation-auditor manoj-github-avio/student-api 1
/designer              manoj-github-avio/student-api 1 path/to/sdd.docx
/orchestrator          manoj-github-avio/student-api 1
/orchestrator          manoj-github-avio/student-api 1 path/to/sdd.docx
```

Each slash command tells Claude to run the corresponding `code-analyzer` CLI subcommand
and show the output. Individual agents post their own PR comment; the orchestrator posts
a combined report.

---

## Follow-up Questions

After any agent finishes its analysis, you'll be prompted to ask follow-up questions interactively:

```
--- Summarizer Follow-up Chat ---
Type 'exit' or press Enter to quit.

> What does the flow-ref bug mean in practice?

The POST endpoint is wired to get-student-applications-impl instead of
post-student-applications-impl. In practice this means any POST request
silently executes the GET logic — the new sub-flow is dead code.

> Is this a blocking bug before merge?
...
```

The initial analysis is prompt-cached, so follow-up turns are fast and cheap.
Type `exit`, `quit`, or press `Enter` to end. Max 10 turns per session.

Works with all commands: `summarizer`, `documentation-auditor`, `designer`, `orchestrator`.

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
              ├── fetch_pr_diff()              GitHub MCP → get_pull_request_files
              ├── run_summarizer()             Anthropic API + MuleSoft skill (prompt cached)
              ├── run_auditor()                GitHub MCP + Anthropic API (prompt cached)
              ├── run_alignment()              local file read + Anthropic API (prompt cached)
              ├── format_summary_comment()     markdown for summarizer PR comment
              ├── format_audit_comment()       markdown for auditor PR comment
              ├── format_alignment_comment()   markdown for designer PR comment
              ├── format_report()              combined orchestrator report (optional alignment)
              └── post_pr_comment()            GitHub MCP → add_issue_comment
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

## Build Log

| Step | What was built | Key concept |
|------|---------------|-------------|
| [Step 1](phases/PHASE_1.md) | MCP server skeleton + `ping` tool | FastMCP, stdio transport |
| [Step 2](phases/PHASE_2.md) | GitHub MCP server integration in Claude Desktop | MCP server composition |
| [Step 3](phases/PHASE_3.md) | Summarizer CLI + Claude Skill format | Prompt caching, skills |
| [Step 4](phases/PHASE_4.md) | Documentation auditor + GitHub MCP client from Python | MCP client SDK, async tools |
| [Step 5](phases/PHASE_5.md) | Design alignment agent + `.docx` support | MCP resources, python-docx |
| [Step 6](phases/PHASE_6.md) | Parallel orchestrator + PR comment posting | `asyncio.gather`, AsyncAnthropic |

See [Claude Concepts](phases/CLAUDE_CONCEPTS.md) for a beginner-friendly explanation of every Claude API and MCP concept used in this project.

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
