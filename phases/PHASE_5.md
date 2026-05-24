# Phase 5: Design Alignment Agent

## What Was Implemented

A `read_design_doc` MCP tool and resource that reads local design documents in any of four
formats (.md, .txt, .docx, .pdf) and exposes them to Claude via both a callable tool and an
MCP resource URI.

A standalone CLI agent (`src/design_alignment_agent.py`) that compares a PR diff against a
design document and reports where the code aligns with or drifts from approved decisions.

A sample design document (`design-doc-sample.docx`) — a real Word file created with
python-docx — that captures architecture decisions for an order processing integration,
including explicit scope boundaries for Phase 1 vs Phase 2/3 features.

---

## Files Added / Modified

| File | Change |
|------|--------|
| `src/server.py` | Added `read_design_doc` tool, `design_doc_resource` MCP resource, `_read_design_doc` helper |
| `src/design_alignment_agent.py` | New CLI agent |
| `design-doc-sample.docx` | Sample design document (real .docx, not markdown) |
| `requirements.txt` | Added `python-docx>=1.0.0` and `pypdf>=4.0.0` |

---

## MCP Tool: `read_design_doc(file_path)`

Reads a local design document and returns its plain-text content.

| Format | Library used |
|--------|-------------|
| `.md`, `.txt` | Built-in `pathlib` |
| `.docx` | `python-docx` — iterates paragraphs, joins non-empty text |
| `.pdf` | `pypdf` — extracts text per page |

```python
# Claude Desktop usage
result = read_design_doc("design-doc-sample.docx")
```

---

## MCP Resource: `design-doc://local/{path}`

This phase demonstrates the **MCP resources primitive** — a different surface from tools.

| Concept | Tool | Resource |
|---------|------|----------|
| What it is | An action Claude invokes | A named piece of content Claude can read |
| How it's identified | By name + arguments | By URI |
| When to use | Imperative operations | Stable, addressable content |

The resource template `design-doc://local/{path}` lets any MCP client read a local design
document by URI without calling a tool:

```
# URI example
design-doc://local/design-doc-sample.docx
design-doc://local/docs/api-design.md
```

In `server.py`:

```python
@mcp.resource("design-doc://local/{path}")
def design_doc_resource(path: str) -> str:
    """Exposes a local design document as an MCP resource."""
    return _read_design_doc(path)
```

---

## CLI Agent: `src/design_alignment_agent.py`

### How to run

```bash
# With a .docx design doc and a diff file
python src/design_alignment_agent.py design-doc-sample.docx sample-mule-pr.diff

# Piped diff
git diff HEAD~1 HEAD | python src/design_alignment_agent.py design-doc-sample.docx

# Any supported format
python src/design_alignment_agent.py design.md my-pr.diff
```

### Example output

```
Reading design document: design-doc-sample.docx
Analyzing alignment (3338 chars)...

=== Design Alignment Report ===
Summary: 3 drift(s) detected, 4 areas aligned with the design

Drift issues detected:
  [HIGH] Phase 1 Scope — Salesforce Integration
          Issue:  PR introduces sfdc:create; design doc defers all Salesforce
                  CRM writes to Phase 2.
          Fix:    Remove sfdc:create, salesforceId variable, and Salesforce config.

  [HIGH] Error Handling — HTTP 503 for DB:CONNECTIVITY
          Issue:  on-error-continue sets HTTP 503; design mandates HTTP 500 for
                  all runtime errors. 503 is reserved for maintenance windows.
          Fix:    Change statusCode="503" to statusCode="500".

  [HIGH] Phase 1 Scope — Multi-Currency Support
          Issue:  PR reads currency from payload; design defers multi-currency
                  to Phase 3.
          Fix:    Remove currency field; hardcode USD.

Aligned with design:
  [OK] Correlation ID captured from inbound request into flow variable
  [OK] ERROR-level logger present in DB error handler with correlationId
  [OK] DataWeave casts amounts to Number and calculates subtotals
  [OK] Flow returns HTTP 200 with orderId on success
```

---

## Architecture Notes

- **No GitHub API calls** — this agent works entirely locally (reads a file, calls Claude).
- **Structured JSON output** — same `_parse_json()` fence-stripping helper used in Phase 4.
- **Format-agnostic reader** — `_read_design_doc()` is defined in both `server.py` (for MCP
  tool access) and `design_alignment_agent.py` (for standalone CLI use).
- **MCP resources vs tools** — resources model stable addressable content; tools model
  imperative actions. This phase uses both for the same underlying file.
