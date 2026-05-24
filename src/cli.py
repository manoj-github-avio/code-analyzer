"""
code-analyzer CLI — unified entry point wrapping all four agents.

Usage (after pip install -e .):
    code-analyzer explainer    <repo> [target] [--test]
    code-analyzer auditor      <repo> [target] [--test]
    code-analyzer designer     <repo> [target] [design-doc] [--test]
    code-analyzer orchestrator <repo> [target] [design-doc] [--test] [--no-post]

Usage (without install):
    python3 src/cli.py <subcommand> ...
"""

import asyncio
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()

# Add src/ to sys.path so command modules can resolve 'from orchestrator import ...'
sys.path.insert(0, str(Path(__file__).parent))


@click.group()
def cli():
    """Code Analyzer — analyze GitHub pull requests with Claude."""


# ── explainer ────────────────────────────────────────────────────────────────

@cli.command("explainer")
@click.argument("repo")
@click.argument("target", required=False, default=None,
                metavar="PR_NUMBER_OR_DIFF")
@click.option("--test", is_flag=True,
              help="Read diff from a local file instead of fetching from GitHub.")
def explainer_cmd(repo, target, test):
    """Explain a PR diff in plain English using Claude.

    \b
    REPO               GitHub repo (owner/repo)
    PR_NUMBER_OR_DIFF  PR number (real mode) or diff file path (--test mode)

    \b
    Examples:
      code-analyzer explainer manoj-github-avio/code-analyzer 5
      code-analyzer explainer manoj-github-avio/code-analyzer --test sample-mule-pr.diff
    """
    from commands.explainer_command import _run
    asyncio.run(_run(repo, target, test))


# ── auditor ──────────────────────────────────────────────────────────────────

@cli.command("auditor")
@click.argument("repo")
@click.argument("target", required=False, default=None,
                metavar="PR_NUMBER_OR_DIFF")
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
      code-analyzer auditor manoj-github-avio/code-analyzer --test sample-mule-pr.diff
    """
    from commands.auditor_command import _run
    asyncio.run(_run(repo, target, test))


# ── designer ─────────────────────────────────────────────────────────────────

@cli.command("designer")
@click.argument("repo")
@click.argument("target", required=False, default=None,
                metavar="PR_NUMBER_OR_DIFF")
@click.argument("design_doc", required=False, default="design-doc-sample.docx",
                metavar="DESIGN_DOC")
@click.option("--test", is_flag=True,
              help="Read diff from a local file instead of fetching from GitHub.")
def designer_cmd(repo, target, design_doc, test):
    """Check a PR diff for alignment with a design document.

    \b
    REPO               GitHub repo (owner/repo)
    PR_NUMBER_OR_DIFF  PR number (real mode) or diff file path (--test mode)
    DESIGN_DOC         Design doc path (.docx/.md/.txt/.pdf) [default: design-doc-sample.docx]

    \b
    Examples:
      code-analyzer designer manoj-github-avio/code-analyzer 5
      code-analyzer designer manoj-github-avio/code-analyzer 5 my-design.docx
      code-analyzer designer manoj-github-avio/code-analyzer --test sample-mule-pr.diff
      code-analyzer designer manoj-github-avio/code-analyzer --test sample-mule-pr.diff design-doc-sample.docx
    """
    from commands.designer_command import _run
    asyncio.run(_run(repo, target, design_doc, test))


# ── orchestrator ──────────────────────────────────────────────────────────────

@cli.command("orchestrator")
@click.argument("repo")
@click.argument("target", required=False, default=None,
                metavar="PR_NUMBER_OR_DIFF")
@click.argument("design_doc", required=False, default="design-doc-sample.docx",
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
    DESIGN_DOC         Design doc path (.docx/.md/.txt/.pdf) [default: design-doc-sample.docx]

    \b
    Examples:
      code-analyzer orchestrator manoj-github-avio/code-analyzer 5
      code-analyzer orchestrator manoj-github-avio/code-analyzer 5 --no-post
      code-analyzer orchestrator manoj-github-avio/code-analyzer --test sample-mule-pr.diff
      code-analyzer orchestrator manoj-github-avio/code-analyzer --test sample-mule-pr.diff design-doc-sample.docx
    """
    from commands.orchestrator_command import _run
    asyncio.run(_run(repo, target, design_doc, test, no_post))


if __name__ == "__main__":
    cli()
