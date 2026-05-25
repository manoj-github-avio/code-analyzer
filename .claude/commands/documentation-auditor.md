Run the code-analyzer documentation auditor agent to check markdown docs for staleness and post a comment to the PR.

Execute this bash command and show the full output:

```bash
code-analyzer documentation-auditor $ARGUMENTS
```

The documentation auditor fetches the PR diff and all markdown files from GitHub, identifies which
docs need updating based on the changes, and posts a comment to the PR with suggested updates.
No comment is posted if no documentation updates are needed.
Use --test to load a local diff file instead (no comment is posted in test mode).

Usage:
  /documentation-auditor <owner/repo> <pr_number>
  /documentation-auditor <owner/repo> <pr_number> --no-post
  /documentation-auditor <owner/repo> --test <diff-file>

Examples:
  /documentation-auditor manoj-github-avio/student-api 1
  /documentation-auditor manoj-github-avio/student-api 1 --no-post
  /documentation-auditor manoj-github-avio/student-api --test samples/sample-mule-pr.diff
