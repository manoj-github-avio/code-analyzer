Run the code-analyzer summarizer agent to explain a PR diff in plain English and post a comment to the PR.

Execute this bash command and show the full output:

```bash
code-analyzer summarizer $ARGUMENTS
```

The summarizer fetches the PR diff from GitHub, produces a plain-English summary and what-changed bullets,
and posts the result as a GitHub PR comment.
Use --test to load a local diff file instead (no comment is posted in test mode).

Usage:
  /summarizer <owner/repo> <pr_number>
  /summarizer <owner/repo> <pr_number> --no-post
  /summarizer <owner/repo> --test <diff-file>

Examples:
  /summarizer manoj-github-avio/student-api 1
  /summarizer manoj-github-avio/student-api 1 --no-post
  /summarizer manoj-github-avio/student-api --test samples/sample-mule-pr.diff
