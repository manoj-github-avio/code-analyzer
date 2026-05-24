Run the code-analyzer designer agent to check a PR diff for alignment with a design document.

Execute this bash command and show the full output:

```bash
code-analyzer designer $ARGUMENTS
```

The designer fetches the PR diff from GitHub (real mode) or reads a local diff file (--test mode),
then compares it against a local design document and reports drift issues and aligned areas.

Usage:
  /designer <owner/repo> <pr_number> [design-doc]
  /designer <owner/repo> --test <diff-file> [design-doc]

Examples:
  /designer manoj-github-avio/code-analyzer 5
  /designer manoj-github-avio/code-analyzer 5 my-design.docx
  /designer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
  /designer manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
