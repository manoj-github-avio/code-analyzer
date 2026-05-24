"""
Explain a PR diff in plain English using Claude.

Real mode fetches the diff from GitHub.
Test mode reads a local diff file — no live PR required.

Usage:
    python3 -m src.commands.explainer_command <owner/repo> <pr_number>
    python3 -m src.commands.explainer_command <owner/repo> --test [diff-file]
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import fetch_pr_diff, run_explainer


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m src.commands.explainer_command",
        description="Explain a PR diff in plain English using Claude.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Real mode — fetch diff from GitHub and analyze:
  python3 -m src.commands.explainer_command manoj-github-avio/code-analyzer 5

  # Test mode — use a local diff file, no live PR needed:
  python3 -m src.commands.explainer_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff
""",
    )
    parser.add_argument("repo", help="GitHub repo in owner/repo format")
    parser.add_argument(
        "target",
        nargs="?",
        help="PR number (real mode) or diff file path (--test mode)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Read diff from a local file instead of fetching from GitHub",
    )
    return parser


async def _run(repo: str, target: str | None, test: bool) -> None:
    if test:
        diff_file = target or "sample-mule-pr.diff"
        path = Path(diff_file)
        if not path.exists():
            print(f"Error: diff file not found: {diff_file}", file=sys.stderr)
            sys.exit(1)
        diff = path.read_text(encoding="utf-8")
        print(f"[TEST] Loaded {len(diff)} chars from {diff_file}", file=sys.stderr)
    else:
        if not target:
            print("Error: pr_number required (or use --test for a local diff)", file=sys.stderr)
            sys.exit(1)
        try:
            pr_number = int(target)
        except ValueError:
            print(f"Error: pr_number must be an integer, got '{target}'", file=sys.stderr)
            sys.exit(1)
        print(f"Fetching diff for {repo} PR #{pr_number}...", file=sys.stderr)
        diff = await fetch_pr_diff(repo, pr_number)
        if not diff.strip():
            print("Error: could not fetch PR diff.", file=sys.stderr)
            sys.exit(1)
        print(f"Fetched {len(diff)} chars.", file=sys.stderr)

    print("Running explainer...", file=sys.stderr)
    t0 = time.perf_counter()
    explanation = await run_explainer(diff)
    elapsed = time.perf_counter() - t0

    print(explanation)
    print(f"\n[Done in {elapsed:.1f}s]", file=sys.stderr)


def main():
    args = _build_parser().parse_args()
    asyncio.run(_run(args.repo, args.target, args.test))


if __name__ == "__main__":
    main()
