# Phase 2: GitHub MCP Server Integration

## Overview

Phase 2 does not add any custom tool code. Instead it wires up the **official open-source GitHub MCP server** (`@modelcontextprotocol/server-github`) so Claude Desktop can read GitHub repositories, pull requests, commits, and files directly — giving the code-analyzer project full GitHub context without us having to write API wrappers ourselves.

---

## What the GitHub MCP Server Provides

The GitHub MCP server exposes the following tools to any connected MCP client:

### Repository tools
| Tool | Description |
|------|-------------|
| `get_file_contents` | Fetch the raw content of any file in a repo |
| `search_repositories` | Search GitHub for repos by keyword |
| `create_repository` | Create a new repository |
| `fork_repository` | Fork a repository |

### Pull request tools
| Tool | Description |
|------|-------------|
| `list_pull_requests` | List open/closed PRs for a repo |
| `get_pull_request` | Get metadata for a specific PR |
| `get_pull_request_diff` | Get the full unified diff of a PR |
| `get_pull_request_files` | List files changed in a PR |
| `get_pull_request_comments` | Get review comments on a PR |
| `get_pull_request_reviews` | Get review decisions on a PR |
| `create_pull_request` | Open a new PR |
| `merge_pull_request` | Merge a PR |

### Commit & branch tools
| Tool | Description |
|------|-------------|
| `list_commits` | List commits on a branch |
| `get_commit` | Get details and diff for a single commit |
| `create_branch` | Create a new branch |
| `push_files` | Push file changes to a branch |

### Issue tools
| Tool | Description |
|------|-------------|
| `list_issues` | List issues for a repo |
| `get_issue` | Get a specific issue |
| `create_issue` | Create a new issue |
| `add_issue_comment` | Comment on an issue |

### Search tools
| Tool | Description |
|------|-------------|
| `search_code` | Search code across GitHub |
| `search_issues` | Search issues and PRs |
| `search_users` | Search GitHub users |

---

## Configuration

### 1. Environment variable

Add to `.env` (and `.env.example` for reference):

```env
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here
```

Generate a token at <https://github.com/settings/tokens> with scopes:
- `repo` — full access to private repos
- `public_repo` — read-only access to public repos only

### 2. Claude Desktop config

The server is registered in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

`npx -y` downloads and runs the server on first use — no global install needed.

---

## How to Use in Claude Desktop

After restarting Claude Desktop, the GitHub tools are available in every conversation. Examples:

### Fetch a PR diff
> "Use get_pull_request_diff to show me the diff for PR #42 in owner/repo"

### List changed files in a PR
> "Use get_pull_request_files to list the files changed in PR #42 in owner/repo"

### Read a specific file
> "Use get_file_contents to show me src/server.py from the main branch of owner/repo"

### Inspect a commit
> "Use get_commit to show me what changed in commit abc1234 in owner/repo"

### List recent commits on a branch
> "Use list_commits to show the last 10 commits on main in owner/repo"

---

## What's NOT in Phase 2

- No new Python code was written
- No changes to `src/server.py`
- No custom GitHub API wrappers

The official MCP server handles all GitHub API communication. Our custom `code-analyzer` server (Phase 1) and the GitHub MCP server run side-by-side as separate MCP servers in Claude Desktop.

---

## Source

- GitHub MCP server: <https://github.com/modelcontextprotocol/servers/tree/main/src/github>
- npm package: `@modelcontextprotocol/server-github`
