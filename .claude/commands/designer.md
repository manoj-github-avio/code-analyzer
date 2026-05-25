Run the code-analyzer designer agent to check a PR diff for alignment with a design document and post a comment to the PR.

Execute this bash command and show the full output:

```bash
code-analyzer designer $ARGUMENTS
```

The designer fetches the PR diff from GitHub, compares it against a local design document,
and posts a comment to the PR with any drift issues found (high/medium severity only).
Use --test to load a local diff file instead (no comment is posted in test mode).

Usage:
  /designer <owner/repo> <pr_number> [design-doc]
  /designer <owner/repo> <pr_number> [design-doc] --no-post
  /designer <owner/repo> --test <diff-file> [design-doc]

Examples:
  /designer manoj-github-avio/student-api 1 /path/to/sdd.docx
  /designer manoj-github-avio/student-api 1 --no-post
  /designer manoj-github-avio/student-api --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
