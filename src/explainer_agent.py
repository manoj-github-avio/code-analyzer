"""
Explain a MuleSoft PR diff in plain English using the Claude API.

Usage:
    python src/explainer_agent.py samples/sample-mule-pr.diff
    cat my.diff | python src/explainer_agent.py
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv()

SKILLS_DIR = Path(__file__).parent.parent / "skills"

SYSTEM_PROMPT = """You are an expert MuleSoft integration engineer who also excels at \
explaining technical changes to non-technical stakeholders.

Your job is to read a MuleSoft PR diff and produce a clear, plain-English explanation that is \
useful to two audiences simultaneously:
1. Developers unfamiliar with MuleSoft (who know code but not Anypoint Platform).
2. Non-technical readers (business analysts, QA, product owners).

Structure your explanation as follows:

## Summary
One or two sentences. What does this change do, in plain English?

## What changed
Bullet list of the specific modifications — flows added/removed/modified, connectors touched, \
DataWeave transformations updated, error handling changes. No XML dumps; describe in plain terms.

## Systems involved
Which external systems (APIs, databases, queues, Salesforce, etc.) does this change interact with? \
Are any new dependencies introduced?

## Data flow
How does data move through the changed code? What comes in, how is it transformed, and what goes out?

## Error handling
What happens when something goes wrong? Are new failure modes introduced or handled?

## Impact assessment
Is this a breaking change? What would break if this was deployed today? \
Who should be notified or needs to test this?

Use plain sentences. Avoid XML snippets. Define any MuleSoft terms you use on first mention.
"""


def load_skill(name: str) -> str:
    skill_path = SKILLS_DIR / name / "SKILL.md"
    if not skill_path.exists():
        return ""
    return skill_path.read_text(encoding="utf-8")


def read_diff() -> str:
    if len(sys.argv) > 1:
        diff_path = Path(sys.argv[1])
        if not diff_path.exists():
            print(f"Error: file not found: {diff_path}", file=sys.stderr)
            sys.exit(1)
        return diff_path.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Usage: python src/explainer_agent.py <diff-file>", file=sys.stderr)
    print("       cat my.diff | python src/explainer_agent.py", file=sys.stderr)
    sys.exit(1)


def explain(diff: str) -> str:
    client = anthropic.Anthropic()
    mulesoft_knowledge = load_skill("mulesoft")

    system_blocks = []

    # Cache the stable MuleSoft knowledge base
    if mulesoft_knowledge:
        system_blocks.append({
            "type": "text",
            "text": mulesoft_knowledge,
            "cache_control": {"type": "ephemeral"},
        })

    # The explanation instructions are also stable — cache them too
    system_blocks.append({
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    })

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=system_blocks,
        messages=[
            {
                "role": "user",
                "content": f"Please explain the following MuleSoft PR diff:\n\n```diff\n{diff}\n```",
            }
        ],
    ) as stream:
        explanation = ""
        for text in stream.text_stream:
            print(text, end="", flush=True)
            explanation += text

    print()  # final newline

    final = stream.get_final_message()
    cached = final.usage.cache_read_input_tokens
    written = final.usage.cache_creation_input_tokens
    if written or cached:
        print(
            f"\n[cache: {written} tokens written, {cached} tokens read]",
            file=sys.stderr,
        )

    return explanation


def main():
    diff = read_diff()
    if not diff.strip():
        print("Error: diff is empty.", file=sys.stderr)
        sys.exit(1)
    explain(diff)


if __name__ == "__main__":
    main()
