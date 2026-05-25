Run all pr-analyzer agents in parallel and produce a full PR analysis report.

Execute this bash command and show the full output:

```bash
pr-analyzer orchestrator $ARGUMENTS
```

The orchestrator runs the summarizer and documentation auditor always.
It runs the design alignment agent only if a design document is provided.
Sections with no content (no doc updates, no design doc) are omitted from the report.
In real mode it fetches the diff from GitHub and posts the report as a PR comment.
Use --no-post to preview without posting. Use --test to load a local diff file.

Usage:
  /pr-analyzer <owner/repo> <pr_number>
  /pr-analyzer <owner/repo> <pr_number> <design-doc>
  /pr-analyzer <owner/repo> <pr_number> <design-doc> --no-post
  /pr-analyzer <owner/repo> --test <diff-file>
  /pr-analyzer <owner/repo> --test <diff-file> <design-doc>

Examples:
  /pr-analyzer manoj-github-avio/student-api 1
  /pr-analyzer manoj-github-avio/student-api 1 /Users/mambolla/Downloads/SDD-Tarleton-Integration-Solution-Design.docx
  /pr-analyzer manoj-github-avio/student-api 1 --no-post
  /pr-analyzer manoj-github-avio/student-api --test samples/sample-mule-pr.diff
  /pr-analyzer manoj-github-avio/student-api --test samples/sample-mule-pr.diff samples/design-doc-sample.docx
