"""
FollowUpChat — simple multi-turn conversation after an agent analysis.

The initial context (agent output) is prompt-cached so it is not re-sent
on every turn. Only the new question/answer pairs accumulate each turn.
"""

import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()


class FollowUpChat:
    """Interactive follow-up conversation tied to a specific agent's analysis."""

    def __init__(
        self,
        agent_name: str,
        context_summary: str,
        system_prompt: str,
        max_turns: int = 10,
    ):
        self.agent_name = agent_name
        self.context_summary = context_summary
        self.system_prompt = system_prompt
        self.max_turns = max_turns

    def start(self) -> None:
        """Run the interactive conversation loop."""
        if not sys.stdin.isatty():
            return  # skip in non-interactive mode (pipes, CI)

        client = anthropic.Anthropic()
        messages: list[dict] = []
        first_turn = True
        turns_used = 0

        print(f"\n--- {self.agent_name} Follow-up Chat ---")
        print("Type 'exit' or press Enter to quit.\n")

        for _ in range(self.max_turns):
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input or user_input.lower() in ("exit", "quit"):
                break

            if first_turn:
                # Cache the analysis context alongside the first question
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.context_summary,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": f"\n\n{user_input}",
                        },
                    ],
                })
                first_turn = False
            else:
                messages.append({"role": "user", "content": user_input})

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=messages,
            )

            reply = response.content[0].text
            messages.append({"role": "assistant", "content": reply})
            print(f"\n{reply}\n")
            turns_used += 1

        if turns_used == self.max_turns:
            print(f"[Max {self.max_turns} turns reached. Chat ended.]\n")
