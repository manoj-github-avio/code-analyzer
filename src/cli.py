"""
code-analyzer CLI — unified Click entry point for all four agents.

All agent logic is imported directly from orchestrator.py.

Usage (after pip install -e .):
    code-analyzer summarizer   <repo> [PR_NUMBER_OR_DIFF] [--test]
    code-analyzer auditor      <repo> [PR_NUMBER_OR_DIFF] [--test]
    code-analyzer designer     <repo> [PR_NUMBER_OR_DIFF] [DESIGN_DOC] [--test]
    code-analyzer orchestrator <repo> [PR_NUMBER_OR_DIFF] [DESIGN_DOC] [--test] [--no-post]

Usage (without install):
    python3 src/cli.py <subcommand> ...
"""

import asyncio
import sys
import time
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()

# Add src/ to sys.path so 'from orchestrator import ...' resolves
sys.path.insert(0, str(Path(__file__).parent))


def _load_diff(diff_file: str) -> str:
    path = Path(diff_file)
    if not path.exists():
        click.echo(f"Error: diff file not found: {diff_file}", err=True)
        raise SystemExit(1)
    return path.read_text(encoding="utf-8")


def _resolve_pr(target: str | None) -> int:
    if not target:
        click.echo("Error: PR_NUMBER required (or use --test for a local diff)", err=True)
        raise SystemExit(1)
    try:
        return int(target)
    except ValueError:
        click.echo(f"Error: PR_NUMBER must be an integer, got '{target}'", err=True)
        raise SystemExit(1)


@click.group()
def cli():
    """Code Analyzer — analyze GitHub pull requests with Claude."""


# ── summarizer ───────────────────────────────────────────────────────────────

@cli.command("summarizer")
@click.argument("repo")
@click.argument("target", required=False, default=None, metavar="PR_NUMBER_OR_DIFF")
@click.option("--test", is_flag=True,
              help="Read diff from a local file instead of fetching from GitHub.")
def summarizer_cmd(repo, target, test):
    """Summarize a PR diff in plain English using Claude.

    \b
    REPO               GitHub repo (owner/repo)
    PR_NUMBER_OR_DIFF  PR number (real mode) or diff file path (--test mode)

    \b
    Examples:
      code-analyzer summarizer manoj-github-avio/code-analyzer 5
      code-analyzer summarizer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
    """
    from orchestrator import fetch_pr_diff, run_summarizer

    async def _run():
        if test:
            diff_file = target or "samples/sample-mule-pr.diff"
            diff = _load_diff(diff_file)
            click.echo(f"[TEST] Loaded {len(diff)} chars from {diff_file}", err=True)
        else:
            pr_number = _resolve_pr(target)
            click.echo(f"Fetching diff for {repo} PR #{pr_number}...", err=True)
            diff = await fetch_pr_diff(repo, pr_number)
            if not diff.strip():
                click.echo("Error: could not fetch PR diff.", err=True)
                raise SystemExit(1)
            click.echo(f"Fetched {len(diff)} chars.", err=True)

        click.echo("Running summarizer...", err=True)
        t0 = time.perf_counter()
        explanation = await run_summarizer(diff)
        elapsed = time.perf_counter() - t0

        click.echo(explanation)
        click.echo(f"\n[Done in {elapsed:.1f}s]", err=True)

    asyncio.run(_run())


# ── auditor ──────────────────────────────────────────────────────────────────

@cli.command("auditor")
@click.argument("repo")
@click.argument("target", required=False, default=None, metavar="PR_NUMBER_OR_DIFF")
@click.option("--test", is_flag=True,
              help="Read diff from a local file; markdown files still fetched from GitHub.")
def auditor_cmd(repo, target, test):
    """Audit README and markdown docs against a PR diff.

    \b
    REPO               GitHub repo (owner/repo)
    PR_NUMBER_OR_DIFF  PR number (real mode) or diff file path (--test mode)

    \b
    Examples:
      code-analyzer auditor manoj-github-avio/code-analyzer 5
      code-analyzer auditor manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
    """
    from orchestrator import fetch_pr_diff, run_auditor

    async def _run():
        if test:
            diff_file = target or "samples/sample-mule-pr.diff"
            diff = _load_diff(diff_file)
            click.echo(f"[TEST] Loaded {len(diff)} chars from {diff_file}", err=True)
        else:
            pr_number = _resolve_pr(target)
            click.echo(f"Fetching diff for {repo} PR #{pr_number}...", err=True)
            diff = await fetch_pr_diff(repo, pr_number)
            if not diff.strip():
                click.echo("Error: could not fetch PR diff.", err=True)
                raise SystemExit(1)
            click.echo(f"Fetched {len(diff)} chars.", err=True)

        click.echo(f"Auditing markdown files in {repo}...", err=True)
        t0 = time.perf_counter()
        results = await run_auditor(repo, diff)
        elapsed = time.perf_counter() - t0

        _show_audit(results)
        click.echo(f"[Done in {elapsed:.1f}s]", err=True)

    asyncio.run(_run())


def _show_audit(results: dict) -> None:
    files = results.get("files_to_update", [])
    needs_update = [f for f in files if f.get("status") == "needs_update"]
    up_to_date = [f for f in files if f.get("status") == "up_to_date"]

    click.echo("\n=== Documentation Audit Results ===")
    click.echo(f"Summary: {results.get('summary', '')}\n")

    if needs_update:
        click.echo("Files that need updates:")
        for item in needs_update:
            click.echo(f"  [UPDATE] {item['file']} — {item.get('section', 'General')}")
            if suggestion := item.get("suggestion"):
                click.echo(f"           {suggestion}")

    if up_to_date:
        click.echo("\nFiles up to date:")
        for item in up_to_date:
            click.echo(f"  [OK]     {item['file']}")

    click.echo()


# ── designer ─────────────────────────────────────────────────────────────────

@cli.command("designer")
@click.argument("repo")
@click.argument("target", required=False, default=None, metavar="PR_NUMBER_OR_DIFF")
@click.argument("design_doc", required=False, default="samples/design-doc-sample.docx",
                metavar="DESIGN_DOC")
@click.option("--test", is_flag=True,
              help="Read diff from a local file instead of fetching from GitHub.")
def designer_cmd(repo, target, design_doc, test):
    """Check a PR diff for alignment with a design document.

    \b
    REPO               GitHub repo (owner/repo)
    PR_NUMBER_OR_DIFF  PR number (real mode) or diff file path (--test mode)
    DESIGN_DOC         Design doc path (.docx/.md/.txt/.pdf) [default: samples/design-doc-sample.docx]

    \b
    Examples:
      code-analyzer designer manoj-github-avio/code-analyzer 5
      code-analyzer designer manoj-github-avio/code-analyzer 5 my-design.docx
      code-analyzer designer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
      code-analyzer designer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
    """
    from orchestrator import fetch_pr_diff, run_alignment

    async def _run():
        if test:
            diff_file = target or "samples/sample-mule-pr.diff"
            diff = _load_diff(diff_file)
            click.echo(f"[TEST] Loaded {len(diff)} chars from {diff_file}", err=True)
        else:
            pr_number = _resolve_pr(target)
            click.echo(f"Fetching diff for {repo} PR #{pr_number}...", err=True)
            diff = await fetch_pr_diff(repo, pr_number)
            if not diff.strip():
                click.echo("Error: could not fetch PR diff.", err=True)
                raise SystemExit(1)
            click.echo(f"Fetched {len(diff)} chars.", err=True)

        click.echo(f"Design doc: {design_doc}", err=True)
        click.echo("Checking design alignment...", err=True)
        t0 = time.perf_counter()
        results = await run_alignment(design_doc, diff)
        elapsed = time.perf_counter() - t0

        _show_alignment(results)
        click.echo(f"[Done in {elapsed:.1f}s]", err=True)

    asyncio.run(_run())


def _show_alignment(results: dict) -> None:
    drifts = results.get("drifts", [])
    aligned = results.get("aligned", [])

    click.echo("\n=== Design Alignment Report ===")
    click.echo(f"Summary: {results.get('summary', '')}\n")

    if drifts:
        click.echo("Drift issues detected:")
        for d in drifts:
            severity = d.get("severity", "medium").upper()
            click.echo(f"  [{severity}] {d['area']}")
            click.echo(f"          Issue: {d['issue']}")
            if suggestion := d.get("suggestion"):
                click.echo(f"          Fix:   {suggestion}")
            click.echo()

    if aligned:
        click.echo("Aligned with design:")
        for a in aligned:
            click.echo(f"  [OK] {a}")

    click.echo()


# ── orchestrator ──────────────────────────────────────────────────────────────

@cli.command("orchestrator")
@click.argument("repo")
@click.argument("target", required=False, default=None, metavar="PR_NUMBER_OR_DIFF")
@click.argument("design_doc", required=False, default="samples/design-doc-sample.docx",
                metavar="DESIGN_DOC")
@click.option("--test", is_flag=True,
              help="Read diff from a local file; print report without posting PR comment.")
@click.option("--no-post", is_flag=True,
              help="Real mode: fetch from GitHub but skip posting the PR comment.")
def orchestrator_cmd(repo, target, design_doc, test, no_post):
    """Run all three agents in parallel and post a structured PR comment.

    \b
    REPO               GitHub repo (owner/repo)
    PR_NUMBER_OR_DIFF  PR number (real mode) or diff file path (--test mode)
    DESIGN_DOC         Design doc path (.docx/.md/.txt/.pdf) [default: samples/design-doc-sample.docx]

    \b
    Examples:
      code-analyzer orchestrator manoj-github-avio/code-analyzer 5
      code-analyzer orchestrator manoj-github-avio/code-analyzer 5 --no-post
      code-analyzer orchestrator manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
      code-analyzer orchestrator manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
    """
    from orchestrator import (
        fetch_pr_diff,
        format_report,
        post_pr_comment,
        run_alignment,
        run_auditor,
        run_summarizer,
    )

    async def _run():
        if test:
            diff_file = target or "samples/sample-mule-pr.diff"
            diff = _load_diff(diff_file)
            click.echo(f"[TEST] Loaded {len(diff)} chars from {diff_file}", err=True)
            click.echo("[TEST] Running 3 agents in parallel...", err=True)

            t0 = time.perf_counter()
            explanation, audit, alignment = await asyncio.gather(
                run_summarizer(diff),
                run_auditor(repo, diff),
                run_alignment(design_doc, diff),
            )
            elapsed = time.perf_counter() - t0

            click.echo(f"[TEST] All agents done in {elapsed:.1f}s. Formatting report...", err=True)
            report = format_report(repo, "test", explanation, audit, alignment)
            click.echo(report)
            click.echo(f"\n[TEST] Done. Total: {elapsed:.1f}s. No PR comment posted.", err=True)
        else:
            pr_number = _resolve_pr(target)
            click.echo(f"Fetching diff for {repo} PR #{pr_number}...", err=True)
            diff = await fetch_pr_diff(repo, pr_number)
            if not diff.strip():
                click.echo("Error: could not fetch PR diff.", err=True)
                raise SystemExit(1)
            click.echo(f"Fetched {len(diff)} chars. Running 3 agents in parallel...", err=True)

            t0 = time.perf_counter()
            explanation, audit, alignment = await asyncio.gather(
                run_summarizer(diff),
                run_auditor(repo, diff),
                run_alignment(design_doc, diff),
            )
            elapsed = time.perf_counter() - t0

            click.echo(f"All agents done in {elapsed:.1f}s. Formatting report...", err=True)
            report = format_report(repo, pr_number, explanation, audit, alignment)
            click.echo(report)

            if no_post:
                click.echo("\n[--no-post] Skipped PR comment.", err=True)
            else:
                click.echo("\nPosting comment to PR...", err=True)
                await post_pr_comment(repo, pr_number, report)
                click.echo(f"✓ Posted to {repo} PR #{pr_number}", err=True)

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
