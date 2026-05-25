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

SYSTEM_PROMPT = """You are an expert MuleSoft integration engineer.

Read a MuleSoft PR diff and produce a concise, factual explanation for developers and non-technical readers.

Structure your output as:

## Summary
A factual description of what this change does. Be as detailed as needed — no artificial limits.

## What Changed
3 to 5 bullet points. Each bullet is one major change, described in 1-2 sentences maximum.
Focus on WHAT changed, not HOW. No file-by-file breakdowns, no subsections, no nested bullets.
Example format:
- New POST endpoint added for student application submissions
- New implementation sub-flow added for processing student applications
- Postman environment file added for production testing

Use plain sentences. Define any MuleSoft terms you use on first mention.
Do not include assumptions, guesses, or suggestions about intent.
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
