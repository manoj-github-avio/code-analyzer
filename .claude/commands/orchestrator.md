Run all three code-analyzer agents in parallel and produce a full PR analysis report.

Execute this bash command and show the full output:

```bash
code-analyzer orchestrator $ARGUMENTS
```

The orchestrator runs the summarizer, auditor, and designer agents concurrently using asyncio.gather().
In real mode it fetches the diff from GitHub and posts the report as a PR comment.
In test mode it reads a local diff file and prints the report without posting.
Use --no-post in real mode to preview the report before posting.

Usage:
  /orchestrator <owner/repo> <pr_number> [design-doc]
  /orchestrator <owner/repo> <pr_number> [design-doc] --no-post
  /orchestrator <owner/repo> --test <diff-file> [design-doc]

Examples:
  /orchestrator manoj-github-avio/code-analyzer 5
  /orchestrator manoj-github-avio/code-analyzer 5 --no-post
  /orchestrator manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff
  /orchestrator manoj-github-avio/code-analyzer --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
