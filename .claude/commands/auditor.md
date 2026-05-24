Run the code-analyzer auditor agent to check README and markdown docs for staleness.

Execute this bash command and show the full output:

```bash
code-analyzer auditor $ARGUMENTS
```

The auditor fetches the PR diff from GitHub (real mode) or reads a local diff file (--test mode),
then compares it against every markdown file in the repo and reports which files need updating.

Usage:
  /auditor <owner/repo> <pr_number>
  /auditor <owner/repo> --test <diff-file>

Examples:
  /auditor manoj-github-avio/code-analyzer 5
  /auditor manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
