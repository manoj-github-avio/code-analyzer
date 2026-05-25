# Claude Concepts Used in Code Analyzer

A beginner-friendly reference for the Claude API and platform concepts used in this project.

---

## 1. Claude API — Messages

The Claude API is the core interface for sending text to Claude and receiving a response.

**How it works:**
- Send a `messages.create()` call with a `system` prompt and a list of `messages`
- Each message has a `role` (`"user"` or `"assistant"`) and `content`
- Claude returns the response in `response.content[0].text`

**Example from this project** (`src/orchestrator.py` — `run_summarizer`):
```python
client = anthropic.AsyncAnthropic()
response = await client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
    messages=[{
        "role": "user",
        "content": f"Please explain the following MuleSoft PR diff:\n\n```diff\n{diff}\n```",
    }],
)
result = response.content[0].text
```

---

## 2. Model Selection

Claude models are selected by name in the `model` parameter.

| Model | Use case |
|-------|----------|
| `claude-sonnet-4-6` | Default — fast, capable, cost-effective |
| `claude-opus-4-7` | Most capable, slower, higher cost |
| `claude-haiku-4-5-20251001` | Fastest, lowest cost, simpler tasks |

This project uses `claude-sonnet-4-6` throughout for a balance of speed and quality.

---

## 3. Prompt Caching

Prompt caching lets Claude reuse previously computed context instead of reprocessing it on every API call. This speeds up responses and reduces token costs.

**How it works:**
- Add `"cache_control": {"type": "ephemeral"}` to any system block or message content block
- Claude caches that block for ~5 minutes after it was last used
- Subsequent calls that include the same cached block pay read tokens instead of input tokens (much cheaper and faster)

**When to use it:**
- Stable content that doesn't change between calls: system prompts, knowledge bases, large documents
- Do NOT cache content that changes per request (e.g. the PR diff itself)

**Example — caching the system prompt and MuleSoft knowledge base** (`run_summarizer`):
```python
system_blocks = [
    {
        "type": "text",
        "text": mulesoft_knowledge,            # large, stable knowledge base
        "cache_control": {"type": "ephemeral"},
    },
    {
        "type": "text",
        "text": SYSTEM_PROMPT,                 # stable instructions
        "cache_control": {"type": "ephemeral"},
    },
]
```

**Example — caching a large design document** (`run_alignment`):
```python
messages=[{
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": f"Design document:\n\n{design_doc}",
            "cache_control": {"type": "ephemeral"},  # same file across many PR runs
        },
        {
            "type": "text",
            "text": f"PR diff:\n```diff\n{diff}\n```",  # changes per PR — not cached
        },
    ],
}]
```

---

## 4. Model Context Protocol (MCP)

MCP is an open standard for connecting AI models to external tools and data sources. Instead of building custom integrations for every tool, MCP provides a common protocol.

**Key concepts:**

| Concept | What it is |
|---------|-----------|
| **MCP Server** | A process that exposes tools/resources over stdio or HTTP |
| **MCP Client** | Code that connects to an MCP server and calls its tools |
| **Tool** | A callable function (like `get_pull_request_files`) |
| **Resource** | Static or dynamic data the AI can read (like `design-doc://local/path`) |

**This project uses MCP two ways:**

**As a server** (`src/server.py`) — exposes tools to Claude Desktop:
```python
from fastmcp import FastMCP
mcp = FastMCP("pr-analyzer")

@mcp.tool()
async def run_pr_analyzer(repo: str, pr_number: int | None = None, design_doc_path: str | None = None) -> str:
    """Run full PR analysis including code summary, documentation audit and design alignment on a GitHub PR.
    Finds latest open PR automatically if pr_number not provided."""
    ...

if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
```

**Tool descriptions drive natural language tool selection.** Claude Desktop reads each tool's
docstring and uses it to decide which tool to call based on what you type in chat. This is
why tool descriptions matter:

| User says | Claude picks |
|-----------|-------------|
| "run pr analysis for open PR for student api" | `run_pr_analyzer` |
| "summarize the open PR for student api" | `run_summarizer` |
| "check documentation for open PR for student api" | `run_documentation_auditor` |
| "check design alignment for open PR..." | `run_design_alignment` |

The description `"Finds latest open PR automatically if pr_number not provided."` tells Claude
it can call the tool without a PR number — enabling fully natural conversational requests.

**As a client** (`src/orchestrator.py`) — calls the GitHub MCP server from Python:
```python
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("get_pull_request_files", {
            "owner": owner, "repo": repo_name, "pull_number": pr_number,
        })
```

---

## 5. Multi-Agent Orchestration

Running multiple Claude agents in parallel using Python's `asyncio`.

**How it works:**
- Each agent is an `async` function that makes its own Anthropic API call
- `asyncio.gather()` runs them all concurrently — they don't wait for each other
- Results come back as a tuple in the same order they were passed in

**Example from this project** (`src/orchestrator.py`):
```python
explanation, audit, alignment = await asyncio.gather(
    run_summarizer(diff),             # Summarizer Agent
    run_auditor(repo, diff),          # Documentation Auditor Agent
    run_alignment(design_doc, diff),  # Design Alignment Agent
)
```

All three API calls happen simultaneously, reducing total wall-clock time from ~30s to ~10s.

---

## 6. Claude Platform Skills

Skills are reusable knowledge files injected into Claude's context at runtime — a way to supply domain knowledge that Claude doesn't have built in. They live in `skills/<name>/SKILL.md` and are read at runtime, then sent as a cached system block before the main system prompt.

**Pattern:**
```python
skill_path = Path("skills/mulesoft/SKILL.md")
knowledge = skill_path.read_text(encoding="utf-8")

system_blocks = [
    {"type": "text", "text": knowledge,     "cache_control": {"type": "ephemeral"}},
    {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
]
```

**When to use:**
- **Proprietary or internal knowledge** — internal APIs, custom frameworks, company-specific conventions that Claude hasn't seen in training.
- **Rapidly evolving stacks** — libraries or protocols that postdate Claude's knowledge cutoff.
- **Not needed for mainstream tech** — Claude already has strong built-in knowledge of well-documented technologies. This project initially injected a MuleSoft skill into the summarizer agent, but testing showed the summarizer produced equally accurate output without it. The skill was removed; Claude's built-in MuleSoft knowledge is sufficient.

**Revisit skills when:** you notice Claude making systematic errors about proprietary concepts, internal naming conventions, or frameworks it genuinely hasn't seen — not just because the tech feels niche.

---

## 7. Tool Use (Function Calling)

Claude can call tools (functions) you define, and you handle the results in a multi-turn loop. This project uses MCP tools rather than raw Claude tool use, but the concept is the same.

**How raw Claude tool use works:**
1. Define tools with JSON schemas in the `tools` parameter
2. Claude responds with a `tool_use` content block when it wants to call a function
3. You execute the function and return a `tool_result` block
4. Claude uses the result to continue generating

**How this project works instead:**
Rather than having Claude call tools mid-generation, the Python orchestrator calls MCP tools directly and feeds results to Claude as plain text. This avoids multi-turn loops and keeps each agent call simple and fast.

```python
# Python calls the GitHub MCP tool directly
files = await _github_call(session, "get_pull_request_files", {...})

# Then feeds the result to Claude as context
response = await client.messages.create(
    ...,
    messages=[{"role": "user", "content": f"PR diff:\n{diff}"}],
)
```

---

## 8. Multi-turn Conversations

Claude maintains conversation context through the `messages` array — each request includes the full history of user/assistant turns so far.

**How the messages array works:**
- Each element is `{"role": "user" | "assistant", "content": "..."}` 
- You append each new user question and assistant reply to the array
- On every API call, you send the entire array — Claude sees the full conversation
- There is no server-side session state; the client owns the history

**Example — growing messages array** (`src/follow_up_chat.py`):
```python
messages = []

# Turn 1: first user message (with cached context)
messages.append({
    "role": "user",
    "content": [
        {"type": "text", "text": context_summary, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": user_question},
    ],
})
reply = client.messages.create(..., messages=messages).content[0].text
messages.append({"role": "assistant", "content": reply})

# Turn 2: just the new question
messages.append({"role": "user", "content": "Follow-up question..."})
reply = client.messages.create(..., messages=messages).content[0].text
messages.append({"role": "assistant", "content": reply})
```

**Why caching helps here:**
The first user message contains the full agent analysis (potentially several KB). Without caching, that analysis would be re-sent and re-processed on every follow-up turn. With `cache_control: ephemeral`, the first message is cached for ~5 minutes — subsequent turns only pay for the new question tokens, not the full context.

```
Turn 1: [context(cached) + question1]                 → ~2000 tokens written to cache
Turn 2: [context(cache hit) + Q1 + A1 + question2]   → cache read, only Q1+A1+Q2 billed
Turn 3: [context(cache hit) + Q1+A1+Q2+A2 + question3] → cache read again
```

**This project's implementation** (`src/follow_up_chat.py`):
- First turn: embeds the agent's analysis as a cached content block alongside the question
- Subsequent turns: plain string messages appended to the growing array
- System prompt is also cached (stable across all turns)
- Max 10 turns by default; exits gracefully on `exit`/`quit`/empty input

**Why FollowUpChat is not used in Claude Desktop:**
Claude Desktop natively maintains conversation context — the tool result is already visible in
the chat thread, and you can ask follow-up questions by simply continuing the conversation.
There is no need to implement a custom multi-turn loop because the host (Claude Desktop)
already manages the messages array. `FollowUpChat` is only needed for CLI contexts where there
is no host to manage conversation state between turns.
