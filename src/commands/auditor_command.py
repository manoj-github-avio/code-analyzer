"""
Audit README and markdown docs against a PR diff.

Real mode fetches the diff from GitHub.
Test mode reads a local diff file — GitHub .md files are still fetched for the audit.

Usage:
    python3 -m src.commands.auditor_command <owner/repo> <pr_number>
    python3 -m src.commands.auditor_command <owner/repo> --test [diff-file]
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import fetch_pr_diff, run_auditor


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m src.commands.auditor_command",
        description="Audit README and markdown docs against a PR diff.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Real mode — fetch diff from GitHub and audit:
  python3 -m src.commands.auditor_command manoj-github-avio/code-analyzer 5

  # Test mode — use a local diff file (markdown files still fetched from GitHub):
  python3 -m src.commands.auditor_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff
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
        help="Read diff from a local file; markdown files are still fetched from GitHub",
    )
    return parser


def _display(results: dict) -> None:
    files = results.get("files_to_update", [])
    needs_update = [f for f in files if f.get("status") == "needs_update"]
    up_to_date = [f for f in files if f.get("status") == "up_to_date"]

    print("\n=== README Audit Results ===")
    print(f"Summary: {results.get('summary', '')}\n")

    if needs_update:
        print("Files that need updates:")
        for item in needs_update:
            print(f"  [UPDATE] {item['file']} — {item.get('section', 'General')}")
            if suggestion := item.get("suggestion"):
                print(f"           {suggestion}")

    if up_to_date:
        print("\nFiles up to date:")
        for item in up_to_date:
            print(f"  [OK]     {item['file']}")

    print()


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

    print(f"Auditing markdown files in {repo}...", file=sys.stderr)
    t0 = time.perf_counter()
    results = await run_auditor(repo, diff)
    elapsed = time.perf_counter() - t0

    _display(results)
    print(f"[Done in {elapsed:.1f}s]", file=sys.stderr)


def main():
    args = _build_parser().parse_args()
    asyncio.run(_run(args.repo, args.target, args.test))


if __name__ == "__main__":
    main()
