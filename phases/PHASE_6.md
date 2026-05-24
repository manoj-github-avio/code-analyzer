# Phase 6: Orchestrator + Output Layer

## What Was Implemented

A single orchestrator (`src/orchestrator.py`) that runs all three analysis agents **in parallel**
using `asyncio.gather()`, aggregates their results into a structured markdown report, and posts
that report as a GitHub PR comment.

Four individual command wrappers (`src/commands/`) that expose each agent — and the full
orchestration — as standalone, directly callable entry points with `--help` and `--test` support.

---

## Files Added

| File | Purpose |
|------|---------|
| `src/orchestrator.py` | Shared async functions: fetch diff, run agents, format report, post comment |
| `src/commands/__init__.py` | Exposes all four commands as importable entry points |
| `src/commands/explainer_command.py` | Explain a PR diff in plain English |
| `src/commands/auditor_command.py` | Audit README/markdown files against a diff |
| `src/commands/designer_command.py` | Check alignment with a design document |
| `src/commands/orchestrator_command.py` | Run all three agents in parallel, post PR comment |
| `src/main.py` | Thin entry point — delegates to `orchestrator_command` |

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

### Run individual agents

Each command supports `--help` for full usage, and `--test` for local dry-run mode.

#### Explainer — plain-English PR summary

```bash
# Real mode — fetch diff from GitHub:
python3 -m src.commands.explainer_command manoj-github-avio/code-analyzer 5

# Test mode — use a local diff file:
python3 -m src.commands.explainer_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff

# Help:
python3 -m src.commands.explainer_command --help
```

#### Auditor — README/markdown drift check

```bash
# Real mode:
python3 -m src.commands.auditor_command manoj-github-avio/code-analyzer 5

# Test mode (markdown files are still fetched from GitHub for the audit):
python3 -m src.commands.auditor_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff

# Help:
python3 -m src.commands.auditor_command --help
```

#### Designer — design document alignment check

```bash
# Real mode:
python3 -m src.commands.designer_command manoj-github-avio/code-analyzer 5
python3 -m src.commands.designer_command manoj-github-avio/code-analyzer 5 my-design.docx

# Test mode:
python3 -m src.commands.designer_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff
python3 -m src.commands.designer_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff design-doc-sample.docx

# Help:
python3 -m src.commands.designer_command --help
```

---

### Run all agents together (orchestrator)

```bash
# Real mode — fetch diff, run all agents, post PR comment:
python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer 5
python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer 5 my-design.docx

# Real mode without posting (preview the report):
python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer 5 --no-post

# Test mode — local diff, no PR comment:
python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff
python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff design-doc-sample.docx

# Via main.py (same as orchestrator_command):
python3 src/main.py manoj-github-avio/code-analyzer 5 design-doc-sample.docx
python3 src/main.py manoj-github-avio/code-analyzer --test sample-mule-pr.diff design-doc-sample.docx

# Help:
python3 -m src.commands.orchestrator_command --help
```

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

- **Individual commands** — each `src/commands/*_command.py` is a standalone entry point
  that can be invoked with `python3 -m src.commands.<name>`. They share business logic
  via `src/orchestrator.py` — no duplication.
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
