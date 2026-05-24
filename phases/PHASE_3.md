# Phase 3: Code Explainer Agent

## What Was Implemented

A standalone Python script (`src/explainer_agent.py`) that reads a MuleSoft PR diff and produces
a plain-English explanation readable by both MuleSoft developers and non-technical stakeholders.

A MuleSoft knowledge skill (`skills/mulesoft/SKILL.md`) structured as a proper Claude Skill
with YAML frontmatter — discoverable by Claude Code, cacheable by the Anthropic API, and
reusable across future agents (Phase 4, 5, 6) without duplication.

A sample diff (`sample-mule-pr.diff`) for local testing without needing a real GitHub PR.

---

## Files Added

| File | Purpose |
|------|---------|
| `src/explainer_agent.py` | CLI script — sends a diff to Claude, streams the explanation |
| `skills/mulesoft/SKILL.md` | MuleSoft knowledge skill — proper Claude Skill format |
| `sample-mule-pr.diff` | Realistic sample diff for testing |

---

## Claude Skill Format

Skills live in `skills/<name>/SKILL.md` and begin with YAML frontmatter:

```markdown
---
name: mulesoft
description: Expert MuleSoft Anypoint Platform knowledge — flows, DataWeave, connectors,
             error handling, and PR review patterns.
version: "1.0"
tags: [mulesoft, integration, dataweave, anypoint, xml]
---

# MuleSoft Integration Expert
...knowledge content...
```

### Why this structure?

| Property | Value |
|----------|-------|
| **Discoverable** | Claude Code reads `skills/*/SKILL.md` automatically — no registration step needed. |
| **Reusable** | Any agent loads a skill by name: `load_skill("mulesoft")`. |
| **Cacheable** | Stable skill content is sent as a cached system block (prompt caching); repeat runs cost ~10% of normal input price. |
| **Versioned** | `version:` field lets you evolve a skill without breaking agents pinned to an older copy. |

### Reusing a skill in another agent

```python
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"

def load_skill(name: str) -> str:
    skill_path = SKILLS_DIR / name / "SKILL.md"
    if not skill_path.exists():
        return ""
    return skill_path.read_text(encoding="utf-8")

# Load it as a cached system block
skill_text = load_skill("mulesoft")
system_blocks = [
    {"type": "text", "text": skill_text, "cache_control": {"type": "ephemeral"}},
    {"type": "text", "text": YOUR_AGENT_INSTRUCTIONS},
]
```

Phase 4, 5, and 6 agents can reuse `load_skill("mulesoft")` without copying knowledge content.

---

## How to Run

### Prerequisites

```bash
pip install -e .
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

### Run with the sample diff

```bash
python src/explainer_agent.py sample-mule-pr.diff
```

### Run with a real diff

```bash
git diff HEAD~1 HEAD -- "*.xml" | python src/explainer_agent.py
python src/explainer_agent.py my-pr.diff
```

---

## How It Works

1. The script reads a diff from a file argument or stdin.
2. It loads `skills/mulesoft/SKILL.md` via `load_skill("mulesoft")`.
3. It calls the Claude API (`claude-sonnet-4-6`) with:
   - The MuleSoft skill as a cached system block.
   - The explanation instructions as a second cached system block.
   - The diff as the user message.
4. The response streams to stdout as it arrives.
5. Cache statistics (tokens written / read) print to stderr after completion.

### Prompt caching

The MuleSoft skill and explanation instructions are marked `cache_control: ephemeral`.
On the first run the API writes them to cache (slightly higher cost). On subsequent runs
within 5 minutes the cached prefix is reused at ~10% of the normal input token cost.

---

## Architecture Notes

- **No custom tools** — single API call with streaming, not an agent loop.
- **Adaptive thinking** — `thinking: {type: "adaptive"}` lets Claude reason through complex
  diffs before producing the explanation.
- **Generic skill loader** — `load_skill(name)` works for any skill in `skills/*/SKILL.md`,
  making it trivial for Phase 4–6 agents to add domain knowledge without boilerplate.
