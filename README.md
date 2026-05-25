# PR Analyzer

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

After `pip install -e .`, the `pr-analyzer` command is available anywhere in the virtualenv:

```bash
# Orchestrator — run all agents, post combined PR comment:
pr-analyzer orchestrator manoj-github-avio/student-api 1
pr-analyzer orchestrator manoj-github-avio/student-api 1 path/to/sdd.docx   # with design doc
pr-analyzer orchestrator manoj-github-avio/student-api 1 --no-post          # preview without posting

# Test mode — local diff file, no GitHub PR needed:
pr-analyzer orchestrator manoj-github-avio/student-api --test samples/sample-mule-pr.diff
pr-analyzer orchestrator manoj-github-avio/student-api --test samples/sample-mule-pr.diff samples/design-doc-sample.docx

# Individual agents — each posts its own PR comment:
pr-analyzer summarizer manoj-github-avio/student-api 1
pr-analyzer documentation-auditor manoj-github-avio/student-api 1
pr-analyzer designer manoj-github-avio/student-api 1 path/to/sdd.docx

# Preview individual agents without posting:
pr-analyzer summarizer manoj-github-avio/student-api 1 --no-post
pr-analyzer documentation-auditor manoj-github-avio/student-api 1 --no-post

# Test mode for individual agents:
pr-analyzer summarizer manoj-github-avio/student-api --test samples/sample-mule-pr.diff
pr-analyzer documentation-auditor manoj-github-avio/student-api --test samples/sample-mule-pr.diff
pr-analyzer designer manoj-github-avio/student-api --test samples/sample-mule-pr.diff samples/design-doc-sample.docx

# Help:
pr-analyzer --help
pr-analyzer summarizer --help
pr-analyzer orchestrator --help
```

### From Claude Code (slash commands)

Four slash commands are defined in `.claude/commands/` and available inside any Claude Code
session opened in this project:

```
/pr-analyzer           manoj-github-avio/student-api 1
/pr-analyzer           manoj-github-avio/student-api 1 path/to/sdd.docx
/summarizer            manoj-github-avio/student-api 1
/documentation-auditor manoj-github-avio/student-api 1
/designer              manoj-github-avio/student-api 1 path/to/sdd.docx
```

Each slash command tells Claude to run the corresponding `pr-analyzer` CLI subcommand
and show the output. Individual agents post their own PR comment; `/pr-analyzer` posts
a combined report.

### From Claude Desktop (natural language)

Once the MCP server is configured (see [Claude Desktop Integration](#claude-desktop-integration)),
you can use natural language in Claude Desktop:

```
"run pr analysis for open PR for student api"
"summarize the open PR for student api"
"check documentation for open PR for student api"
"check design alignment for open PR for student api path/to/sdd.docx"
```

Claude Desktop picks the right tool from the description, auto-finds the latest open PR if
you don't specify a number, runs the analysis, posts a PR comment, and shows the report in chat.

---

## Follow-up Questions

After any CLI/slash command agent finishes, you'll be prompted to ask follow-up questions
interactively:

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

Works with all CLI commands: `summarizer`, `documentation-auditor`, `designer`, `orchestrator`.

In Claude Desktop, follow-ups are handled natively — just continue the conversation in chat.

---

## Architecture

```
Three entry points — same underlying logic:

.claude/commands/*.md    ← /slash commands in Claude Code
        │                   each tells Claude to run: pr-analyzer <subcommand> ...
        ▼
src/cli.py               ← Click CLI, registered as 'pr-analyzer' console script
        │
        ├── src/server.py            ← FastMCP server for Claude Desktop (natural language)
        │     ├── run_pr_analyzer()        all agents in parallel, auto-find open PR
        │     ├── run_summarizer()         summarizer only, auto-find open PR
        │     ├── run_documentation_auditor() auditor only, auto-find open PR
        │     └── run_design_alignment()   alignment only, auto-find open PR
        │
        └── src/orchestrator.py      ← all async agent logic
              ├── fetch_pr_diff()              GitHub MCP → get_pull_request_files
              ├── run_summarizer()             Anthropic API (prompt cached)
              ├── run_auditor()                GitHub MCP + Anthropic API (prompt cached)
              ├── run_alignment()              local file read + Anthropic API (prompt cached)
              ├── format_summary_comment()     markdown for summarizer PR comment
              ├── format_audit_comment()       markdown for auditor PR comment
              ├── format_alignment_comment()   markdown for designer PR comment
              ├── format_report()              combined orchestrator report (optional alignment)
              └── post_pr_comment()            GitHub MCP → add_issue_comment
```

### MCP server tools (src/server.py)

| Tool | Description |
|------|-------------|
| `run_pr_analyzer(repo, pr_number?, design_doc_path?)` | Full analysis: summarizer + auditor + alignment. Auto-finds latest open PR. |
| `run_summarizer(repo, pr_number?)` | Summarize PR in plain English. Auto-finds latest open PR. |
| `run_documentation_auditor(repo, pr_number?)` | Audit markdown docs. Auto-finds latest open PR. |
| `run_design_alignment(repo, pr_number?, design_doc_path?)` | Check design alignment. Auto-finds latest open PR. |
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
| [Step 3](phases/PHASE_3.md) | Summarizer CLI + prompt caching | Prompt caching |
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
    "pr-analyzer": {
      "command": "/path/to/.venv/bin/python",
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

Once configured, Claude Desktop has access to all four analysis tools and will select the
right one based on your natural language request. The `github` MCP server entry is required
for the pr-analyzer tools to fetch PR diffs and post comments.
