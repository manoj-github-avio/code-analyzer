# Phase 6: Orchestrator + Output Layer

## What Was Implemented

A single orchestrator (`src/orchestrator.py`) that runs all three analysis agents **in parallel**
using `asyncio.gather()`, aggregates their results into a structured markdown report, and posts
that report as a GitHub PR comment.

Two complementary entry points that expose the same underlying logic:
- **`src/cli.py`** — Click CLI registered as the `code-analyzer` shell command
- **`.claude/commands/`** — four Claude Code slash commands (`/explainer`, `/auditor`,
  `/designer`, `/orchestrator`)

---

## Files Added

| File | Purpose |
|------|---------|
| `src/orchestrator.py` | All async agent logic: fetch diff, run agents, format report, post comment |
| `src/cli.py` | Click CLI — `code-analyzer` shell command with four subcommands |
| `src/main.py` | Thin entry point — `python3 src/main.py` delegates to orchestrator subcommand |
| `.claude/commands/explainer.md` | `/explainer` slash command for Claude Code |
| `.claude/commands/auditor.md` | `/auditor` slash command for Claude Code |
| `.claude/commands/designer.md` | `/designer` slash command for Claude Code |
| `.claude/commands/orchestrator.md` | `/orchestrator` slash command for Claude Code |

---

## How to Run

### Prerequisites

```bash
pip install -e .

# .env must contain both:
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
```

---

### Option 1: CLI in the terminal

The `code-analyzer` console script is registered by `pyproject.toml` and callable from anywhere
in the virtualenv after `pip install -e .`. Each subcommand supports `--help` and `--test`.

```bash
# Explainer — plain-English PR summary
code-analyzer explainer manoj-github-avio/code-analyzer 5
code-analyzer explainer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff

# Auditor — README/markdown drift check
code-analyzer auditor manoj-github-avio/code-analyzer 5
code-analyzer auditor manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff

# Designer — design document alignment
code-analyzer designer manoj-github-avio/code-analyzer 5
code-analyzer designer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx

# Orchestrator — all three agents + PR comment
code-analyzer orchestrator manoj-github-avio/code-analyzer 5
code-analyzer orchestrator manoj-github-avio/code-analyzer 5 --no-post        # preview, no post
code-analyzer orchestrator manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx

# Help
code-analyzer --help
code-analyzer explainer --help
```

---

### Option 2: Slash commands in Claude Code

Four project-level slash commands in `.claude/commands/` are available as `/explainer`,
`/auditor`, `/designer`, and `/orchestrator` in any Claude Code session opened in this repo.

> **Note:** Claude Code uses `/command` (slash), not `@command`. Slash commands are the
> correct Claude Code shortcut system.

```
/explainer    manoj-github-avio/code-analyzer 5
/explainer    manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff

/auditor      manoj-github-avio/code-analyzer 5
/auditor      manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff

/designer     manoj-github-avio/code-analyzer 5
/designer     manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx

/orchestrator manoj-github-avio/code-analyzer 5
/orchestrator manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
```

Each slash command tells Claude to run the corresponding `code-analyzer` CLI subcommand and
display the output. `$ARGUMENTS` in the `.md` file is replaced with whatever you type after
the command name.

---

## Workflow Steps

```
1. fetch_pr_diff(repo, pr_number)          [real mode only]
        │  GitHub MCP server → get_pull_request_files
        │  Reconstructs unified diff from per-file patches
        ▼
2. asyncio.gather(...)   ← all three run concurrently
   ├── run_explainer(diff)
   │     AsyncAnthropic → claude-sonnet-4-6
   │     MuleSoft skill loaded from skills/mulesoft/SKILL.md (prompt cached)
   │     Returns plain-English PR summary
   │
   ├── run_auditor(repo, diff)
   │     GitHub MCP server → search_code / get_file_contents
   │     AsyncAnthropic → claude-sonnet-4-6
   │     Returns {files_to_update, summary}
   │
   └── run_alignment(design_doc_path, diff)
         asyncio.to_thread → _read_design_doc (.docx / .md / .txt / .pdf)
         AsyncAnthropic → claude-sonnet-4-6
         Returns {drifts, aligned, summary}
        │
        ▼
3. format_report(...)
        Combines all three results into a structured markdown comment
        │
        ▼
4. post_pr_comment(repo, pr_number, report)    [real mode, no --no-post]
        GitHub MCP server → add_issue_comment
```

---

## Example Output (PR Comment)

```markdown
## 🤖 Code Analyzer Report

**Repository:** `manoj-github-avio/code-analyzer` &nbsp;|&nbsp; **PR:** #5

---

## 📝 Code Summary

## Summary
This change extends the order-processing integration to push orders into
Salesforce, adds multi-currency support, and revises error handling.

## What changed
- Correlation ID captured from inbound request header
- DataWeave enriched: amounts cast to Number, currency field added
- New step: sfdc:create writes an Order__c record to Salesforce
- DB error handler changed from on-error-propagate to on-error-continue,
  now returns HTTP 503 instead of HTTP 500

## Systems involved
- HTTP (inbound): unchanged, POST /api/orders
- PostgreSQL (existing): order + line-item insert unchanged in structure
- Salesforce (NEW): every order now creates a record in Salesforce CRM

## Error handling
- Database errors now caught, return 503 with "Service temporarily unavailable"
- Salesforce errors propagate to caller as HTTP 500

## Impact assessment
- Breaking: DB outage code changes 500 → 503
- New dependency: Salesforce credentials required in all environments

---

## 📚 README Updates Needed

**1 of 1 files needs updates**

| File | Section | Suggested update |
|------|---------|------------------|
| `README.md` | Tools | Document the new audit and alignment MCP tools added in this PR |

---

## 🏗️ Design Alignment

**3 drift(s) detected, 4 areas aligned**

### ❌ Drift Issues

🔴 **[HIGH] Phase 1 Scope — Salesforce Integration**
- **Issue:** PR adds sfdc:create; design defers Salesforce to Phase 2
- **Fix:** Remove sfdc:create and related config; defer to Phase 2 branch

🔴 **[HIGH] Error Handling — HTTP 503 for DB:CONNECTIVITY**
- **Issue:** Design mandates HTTP 500 for runtime DB errors; 503 is for maintenance
- **Fix:** Change statusCode="503" → statusCode="500"

🔴 **[HIGH] Phase 1 Scope — Multi-Currency**
- **Issue:** currency field from payload; design defers multi-currency to Phase 3
- **Fix:** Remove currency from transform; hardcode USD

### ✅ Aligned with Design

- Correlation ID captured from inbound request as required by design section 3
- ERROR-level logger present in DB error handler with correlationId
- DataWeave casts amounts to Number as required

---

*Generated by [code-analyzer](https://github.com/manoj-github-avio/code-analyzer) — powered by Claude claude-sonnet-4-6*
```

---

## Architecture Notes

- **Two entry points, one logic layer** — `src/cli.py` (terminal) and `.claude/commands/`
  (Claude Code slash commands) both call the same functions in `src/orchestrator.py`.
  No duplication of agent logic.
- **Parallel execution** — `asyncio.gather()` runs all three agents concurrently. The auditor
  opens its own short-lived GitHub MCP server subprocess.
- **Async Anthropic client** — `anthropic.AsyncAnthropic()` lets all three Claude calls
  run inside the same event loop without blocking.
- **`asyncio.to_thread()`** — `_read_design_doc()` is synchronous (file I/O + python-docx);
  wrapped so it doesn't block the event loop.
- **GitHub MCP for everything GitHub** — PR diff fetch, .md file discovery, and PR comment
  posting all go through the GitHub MCP server. No direct HTTP calls to the GitHub API.
- **Prompt caching** — the MuleSoft skill system block is marked `cache_control: ephemeral`;
  repeated runs within 5 minutes reuse the cached prefix at ~10% token cost.
- **`--test` mode** — all four commands accept `--test <diff-file>` to run against a local
  diff without a live PR. The orchestrator command additionally supports `--no-post` to
  preview the report without posting a GitHub comment.
