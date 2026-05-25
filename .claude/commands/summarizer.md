Run the code-analyzer summarizer agent to explain a PR diff in plain English.

Execute this bash command and show the full output:

```bash
code-analyzer summarizer $ARGUMENTS
```

The summarizer fetches the PR diff from GitHub (real mode) or reads a local diff file (--test mode)
and produces a plain-English explanation covering: summary and what changed.

Usage:
  /summarizer <owner/repo> <pr_number>
  /summarizer <owner/repo> --test <diff-file>

Examples:
  /summarizer manoj-github-avio/code-analyzer 5
  /summarizer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
