"""
code-analyzer CLI — unified Click entry point for all four agents.

All agent logic is imported directly from orchestrator.py.

Usage (after pip install -e .):
    code-analyzer summarizer            <repo> <pr_number> [--test DIFF_FILE] [--no-post]
    code-analyzer documentation-auditor <repo> <pr_number> [--test DIFF_FILE] [--no-post]
    code-analyzer designer              <repo> <pr_number> [DESIGN_DOC] [--test DIFF_FILE] [--no-post]
    code-analyzer orchestrator          <repo> <pr_number> [DESIGN_DOC] [--test DIFF_FILE] [--no-post]

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


def _resolve_pr(value: str | None) -> int:
    if not value:
        click.echo("Error: PR_NUMBER required (or use --test DIFF_FILE for a local diff)", err=True)
        raise SystemExit(1)
    try:
        return int(value)
    except ValueError:
        click.echo(f"Error: PR_NUMBER must be an integer, got '{value}'", err=True)
        raise SystemExit(1)


@click.group()
def cli():
    """Code Analyzer — analyze GitHub pull requests with Claude."""


# ── summarizer ───────────────────────────────────────────────────────────────

@cli.command("summarizer")
@click.argument("repo")
@click.argument("pr_number", required=False, default=None, metavar="PR_NUMBER")
@click.option("--test", default=None, metavar="DIFF_FILE",
              help="Load diff from a local file; output only, no PR comment posted.")
@click.option("--no-post", is_flag=True,
              help="Fetch from GitHub but skip posting the PR comment.")
def summarizer_cmd(repo, pr_number, test, no_post):
    """Summarize a PR diff in plain English and post a comment to the PR.

    \b
    REPO       GitHub repo (owner/repo)
    PR_NUMBER  Pull request number

    \b
    Examples:
      code-analyzer summarizer manoj-github-avio/student-api 1
      code-analyzer summarizer manoj-github-avio/student-api 1 --no-post
      code-analyzer summarizer manoj-github-avio/student-api --test samples/sample-mule-pr.diff
    """
    from orchestrator import fetch_pr_diff, format_summary_comment, post_pr_comment, run_summarizer

    async def _run():
        if test:
            diff = _load_diff(test)
            click.echo(f"[TEST] Loaded {len(diff)} chars from {test}", err=True)
            click.echo("Running summarizer...", err=True)
            t0 = time.perf_counter()
            explanation = await run_summarizer(diff)
            elapsed = time.perf_counter() - t0
            click.echo(format_summary_comment(explanation))
            click.echo(f"\n[Done in {elapsed:.1f}s]", err=True)
        else:
            pr_num = _resolve_pr(pr_number)
            click.echo(f"Fetching diff for {repo} PR #{pr_num}...", err=True)
            diff = await fetch_pr_diff(repo, pr_num)
            if not diff.strip():
                click.echo("Error: could not fetch PR diff.", err=True)
                raise SystemExit(1)
            click.echo(f"Fetched {len(diff)} chars. Running summarizer...", err=True)
            t0 = time.perf_counter()
            explanation = await run_summarizer(diff)
            elapsed = time.perf_counter() - t0
            comment = format_summary_comment(explanation)
            click.echo(comment)
            if no_post:
                click.echo(f"\n[--no-post] Skipped PR comment. Done in {elapsed:.1f}s.", err=True)
            else:
                click.echo(f"\nPosting comment to PR...", err=True)
                await post_pr_comment(repo, pr_num, comment)
                click.echo(f"✓ Posted to {repo} PR #{pr_num}. Done in {elapsed:.1f}s.", err=True)

    asyncio.run(_run())


# ── documentation-auditor ────────────────────────────────────────────────────

@cli.command("documentation-auditor")
@click.argument("repo")
@click.argument("pr_number", required=False, default=None, metavar="PR_NUMBER")
@click.option("--test", default=None, metavar="DIFF_FILE",
              help="Load diff from a local file; output only, no PR comment posted.")
@click.option("--no-post", is_flag=True,
              help="Fetch from GitHub but skip posting the PR comment.")
def documentation_auditor_cmd(repo, pr_number, test, no_post):
    """Audit markdown docs against a PR diff and post a comment to the PR.

    \b
    REPO       GitHub repo (owner/repo)
    PR_NUMBER  Pull request number

    \b
    Examples:
      code-analyzer documentation-auditor manoj-github-avio/student-api 1
      code-analyzer documentation-auditor manoj-github-avio/student-api 1 --no-post
      code-analyzer documentation-auditor manoj-github-avio/student-api --test samples/sample-mule-pr.diff
    """
    from orchestrator import fetch_pr_diff, format_audit_comment, post_pr_comment, run_auditor

    async def _run():
        if test:
            diff = _load_diff(test)
            click.echo(f"[TEST] Loaded {len(diff)} chars from {test}", err=True)
            click.echo(f"Auditing markdown files in {repo}...", err=True)
            t0 = time.perf_counter()
            results = await run_auditor(repo, diff)
            elapsed = time.perf_counter() - t0
            comment = format_audit_comment(results)
            click.echo(comment if comment else "No documentation updates needed.")
            click.echo(f"\n[Done in {elapsed:.1f}s]", err=True)
        else:
            pr_num = _resolve_pr(pr_number)
            click.echo(f"Fetching diff for {repo} PR #{pr_num}...", err=True)
            diff = await fetch_pr_diff(repo, pr_num)
            if not diff.strip():
                click.echo("Error: could not fetch PR diff.", err=True)
                raise SystemExit(1)
            click.echo(f"Fetched {len(diff)} chars. Auditing markdown files in {repo}...", err=True)
            t0 = time.perf_counter()
            results = await run_auditor(repo, diff)
            elapsed = time.perf_counter() - t0
            comment = format_audit_comment(results)
            if comment:
                click.echo(comment)
                if no_post:
                    click.echo(f"\n[--no-post] Skipped PR comment. Done in {elapsed:.1f}s.", err=True)
                else:
                    click.echo(f"\nPosting comment to PR...", err=True)
                    await post_pr_comment(repo, pr_num, comment)
                    click.echo(f"✓ Posted to {repo} PR #{pr_num}. Done in {elapsed:.1f}s.", err=True)
            else:
                click.echo("No documentation updates needed — no comment posted.", err=True)
                click.echo(f"[Done in {elapsed:.1f}s]", err=True)

    asyncio.run(_run())


# ── designer ─────────────────────────────────────────────────────────────────

@cli.command("designer")
@click.argument("repo")
@click.argument("pr_number", required=False, default=None, metavar="PR_NUMBER")
@click.argument("design_doc", required=False, default="samples/design-doc-sample.docx",
                metavar="DESIGN_DOC")
@click.option("--test", default=None, metavar="DIFF_FILE",
              help="Load diff from a local file; output only, no PR comment posted.")
@click.option("--no-post", is_flag=True,
              help="Fetch from GitHub but skip posting the PR comment.")
def designer_cmd(repo, pr_number, design_doc, test, no_post):
    """Check a PR diff against a design document and post a comment to the PR.

    \b
    REPO        GitHub repo (owner/repo)
    PR_NUMBER   Pull request number
    DESIGN_DOC  Design doc path (.docx/.md/.txt/.pdf) [default: samples/design-doc-sample.docx]

    \b
    Examples:
      code-analyzer designer manoj-github-avio/student-api 1 path/to/sdd.docx
      code-analyzer designer manoj-github-avio/student-api 1 --no-post
      code-analyzer designer manoj-github-avio/student-api --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
    """
    from orchestrator import fetch_pr_diff, format_alignment_comment, post_pr_comment, run_alignment

    async def _run():
        if test:
            diff = _load_diff(test)
            click.echo(f"[TEST] Loaded {len(diff)} chars from {test}", err=True)
            click.echo(f"Design doc: {design_doc}", err=True)
            click.echo("Checking design alignment...", err=True)
            t0 = time.perf_counter()
            results = await run_alignment(design_doc, diff)
            elapsed = time.perf_counter() - t0
            click.echo(format_alignment_comment(results))
            click.echo(f"\n[Done in {elapsed:.1f}s]", err=True)
        else:
            pr_num = _resolve_pr(pr_number)
            click.echo(f"Fetching diff for {repo} PR #{pr_num}...", err=True)
            diff = await fetch_pr_diff(repo, pr_num)
            if not diff.strip():
                click.echo("Error: could not fetch PR diff.", err=True)
                raise SystemExit(1)
            click.echo(f"Fetched {len(diff)} chars. Design doc: {design_doc}", err=True)
            click.echo("Checking design alignment...", err=True)
            t0 = time.perf_counter()
            results = await run_alignment(design_doc, diff)
            elapsed = time.perf_counter() - t0
            comment = format_alignment_comment(results)
            click.echo(comment)
            if no_post:
                click.echo(f"\n[--no-post] Skipped PR comment. Done in {elapsed:.1f}s.", err=True)
            else:
                click.echo(f"\nPosting comment to PR...", err=True)
                await post_pr_comment(repo, pr_num, comment)
                click.echo(f"✓ Posted to {repo} PR #{pr_num}. Done in {elapsed:.1f}s.", err=True)

    asyncio.run(_run())


# ── orchestrator ──────────────────────────────────────────────────────────────

@cli.command("orchestrator")
@click.argument("repo")
@click.argument("pr_number", required=False, default=None, metavar="PR_NUMBER")
@click.argument("design_doc", required=False, default=None, metavar="DESIGN_DOC")
@click.option("--test", default=None, metavar="DIFF_FILE",
              help="Load diff from a local file; print report without posting PR comment.")
@click.option("--no-post", is_flag=True,
              help="Fetch from GitHub but skip posting the PR comment.")
def orchestrator_cmd(repo, pr_number, design_doc, test, no_post):
    """Run agents in parallel and post a structured PR comment.

    Always runs summarizer. Runs documentation auditor always. Runs design
    alignment only if DESIGN_DOC is provided. Omits sections with no content.

    \b
    REPO        GitHub repo (owner/repo)
    PR_NUMBER   Pull request number
    DESIGN_DOC  Optional design doc path (.docx/.md/.txt/.pdf)

    \b
    Examples:
      code-analyzer orchestrator manoj-github-avio/student-api 1
      code-analyzer orchestrator manoj-github-avio/student-api 1 path/to/sdd.docx
      code-analyzer orchestrator manoj-github-avio/student-api 1 --no-post
      code-analyzer orchestrator manoj-github-avio/student-api --test samples/sample-mule-pr.diff
      code-analyzer orchestrator manoj-github-avio/student-api --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
    """
    from orchestrator import (
        fetch_pr_diff,
        format_report,
        post_pr_comment,
        run_alignment,
        run_auditor,
        run_summarizer,
    )

    async def _gather(diff: str):
        if design_doc:
            explanation, audit, alignment = await asyncio.gather(
                run_summarizer(diff), run_auditor(repo, diff), run_alignment(design_doc, diff),
            )
        else:
            explanation, audit = await asyncio.gather(
                run_summarizer(diff), run_auditor(repo, diff),
            )
            alignment = None
        return explanation, audit, alignment

    async def _run():
        if test:
            diff = _load_diff(test)
            n = "3" if design_doc else "2"
            click.echo(f"[TEST] Loaded {len(diff)} chars from {test}", err=True)
            click.echo(f"[TEST] Running {n} agents in parallel...", err=True)
            t0 = time.perf_counter()
            explanation, audit, alignment = await _gather(diff)
            elapsed = time.perf_counter() - t0
            click.echo(f"[TEST] All agents done in {elapsed:.1f}s. Formatting report...", err=True)
            click.echo(format_report(explanation, audit, alignment))
            click.echo(f"\n[TEST] Done. Total: {elapsed:.1f}s. No PR comment posted.", err=True)
        else:
            pr_num = _resolve_pr(pr_number)
            click.echo(f"Fetching diff for {repo} PR #{pr_num}...", err=True)
            diff = await fetch_pr_diff(repo, pr_num)
            if not diff.strip():
                click.echo("Error: could not fetch PR diff.", err=True)
                raise SystemExit(1)
            n = "3" if design_doc else "2"
            click.echo(f"Fetched {len(diff)} chars. Running {n} agents in parallel...", err=True)
            t0 = time.perf_counter()
            explanation, audit, alignment = await _gather(diff)
            elapsed = time.perf_counter() - t0
            click.echo(f"All agents done in {elapsed:.1f}s. Formatting report...", err=True)
            report = format_report(explanation, audit, alignment)
            click.echo(report)
            if no_post:
                click.echo("\n[--no-post] Skipped PR comment.", err=True)
            else:
                click.echo("\nPosting comment to PR...", err=True)
                await post_pr_comment(repo, pr_num, report)
                click.echo(f"✓ Posted to {repo} PR #{pr_num}", err=True)

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
