"""
Run all three analysis agents in parallel and post a structured PR comment.

Real mode fetches the diff from GitHub and posts a PR comment.
Test mode reads a local diff file and prints the report without posting.

Usage:
    python3 -m src.commands.orchestrator_command <owner/repo> <pr_number> [design-doc]
    python3 -m src.commands.orchestrator_command <owner/repo> --test [diff-file] [design-doc]
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import (
    fetch_pr_diff,
    format_report,
    post_pr_comment,
    run_alignment,
    run_auditor,
    run_explainer,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m src.commands.orchestrator_command",
        description=(
            "Run all three analysis agents in parallel. "
            "Posts a structured PR comment in real mode."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Real mode — fetch diff, run all agents, post PR comment:
  python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer 5
  python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer 5 my-design.docx

  # Real mode without posting:
  python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer 5 --no-post

  # Test mode — use a local diff file, print report, no PR comment:
  python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff
  python3 -m src.commands.orchestrator_command manoj-github-avio/code-analyzer --test sample-mule-pr.diff design-doc-sample.docx
""",
    )
    parser.add_argument("repo", help="GitHub repo in owner/repo format")
    parser.add_argument(
        "target",
        nargs="?",
        help="PR number (real mode) or diff file path (--test mode)",
    )
    parser.add_argument(
        "design_doc",
        nargs="?",
        default="design-doc-sample.docx",
        help="Path to design doc (.docx, .md, .txt, .pdf) [default: design-doc-sample.docx]",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Read diff from a local file; print report without posting PR comment",
    )
    parser.add_argument(
        "--no-post",
        action="store_true",
        help="Real mode: fetch from GitHub but skip posting PR comment",
    )
    return parser


async def _run(
    repo: str,
    target: str | None,
    design_doc: str,
    test: bool,
    no_post: bool,
) -> None:
    if test:
        diff_file = target or "sample-mule-pr.diff"
        path = Path(diff_file)
        if not path.exists():
            print(f"Error: diff file not found: {diff_file}", file=sys.stderr)
            sys.exit(1)
        diff = path.read_text(encoding="utf-8")
        print(f"[TEST] Loaded {len(diff)} chars from {diff_file}", file=sys.stderr)
        print("[TEST] Running 3 agents in parallel...", file=sys.stderr)

        t0 = time.perf_counter()
        explanation, audit, alignment = await asyncio.gather(
            run_explainer(diff),
            run_auditor(repo, diff),
            run_alignment(design_doc, diff),
        )
        elapsed = time.perf_counter() - t0

        print(f"[TEST] All agents done in {elapsed:.1f}s. Formatting report...", file=sys.stderr)
        report = format_report(repo, "test", explanation, audit, alignment)
        print(report)
        print(f"\n[TEST] Done. Total: {elapsed:.1f}s. No PR comment posted.", file=sys.stderr)
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
        print(f"Fetched {len(diff)} chars. Running 3 agents in parallel...", file=sys.stderr)

        t0 = time.perf_counter()
        explanation, audit, alignment = await asyncio.gather(
            run_explainer(diff),
            run_auditor(repo, diff),
            run_alignment(design_doc, diff),
        )
        elapsed = time.perf_counter() - t0

        print(f"All agents done in {elapsed:.1f}s. Formatting report...", file=sys.stderr)
        report = format_report(repo, pr_number, explanation, audit, alignment)
        print(report)

        if no_post:
            print("\n[--no-post] Skipped PR comment.", file=sys.stderr)
        else:
            print("\nPosting comment to PR...", file=sys.stderr)
            await post_pr_comment(repo, pr_number, report)
            print(f"✓ Posted to {repo} PR #{pr_number}", file=sys.stderr)


def main():
    args = _build_parser().parse_args()
    asyncio.run(_run(args.repo, args.target, args.design_doc, args.test, args.no_post))


if __name__ == "__main__":
    main()
