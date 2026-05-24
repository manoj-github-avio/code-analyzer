Run the code-analyzer explainer agent to explain a PR diff in plain English.

Execute this bash command and show the full output:

```bash
code-analyzer explainer $ARGUMENTS
```

The explainer fetches the PR diff from GitHub (real mode) or reads a local diff file (--test mode)
and produces a plain-English explanation covering: summary, what changed, systems involved,
data flow, error handling, and impact assessment.

Usage:
  /explainer <owner/repo> <pr_number>
  /explainer <owner/repo> --test <diff-file>

Examples:
  /explainer manoj-github-avio/code-analyzer 5
  /explainer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
