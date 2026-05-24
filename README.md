# Code Analyzer

A Python MCP (Model Context Protocol) server for analyzing GitHub repositories. This project provides a suite of tools that enable AI assistants to inspect, analyze, and understand codebases programmatically.

## Features

- MCP server built with [fastmcp](https://github.com/jlowin/fastmcp)
- GitHub repository analysis tools
- Incremental functionality delivered across 6 phases

## Requirements

- Python 3.11+
- A GitHub personal access token

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/manoj-github-avio/code-analyzer.git
cd code-analyzer
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -e .
```

Or using requirements.txt:

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your GITHUB_TOKEN
```

### 5. Run the MCP server

```bash
python src/server.py
```

## Project Phases

| Phase | Description |
|-------|-------------|
| [Phase 1](phases/PHASE_1.md) | MCP server skeleton with ping tool |
| [Phase 2](phases/PHASE_2.md) | GitHub repository metadata fetching |
| [Phase 3](phases/PHASE_3.md) | File tree and content retrieval |
| [Phase 4](phases/PHASE_4.md) | Code search and pattern matching |
| [Phase 5](phases/PHASE_5.md) | Dependency and language analysis |
| [Phase 6](phases/PHASE_6.md) | Summary and reporting tools |

## Development

This project uses [fastmcp](https://github.com/jlowin/fastmcp) to expose tools over the Model Context Protocol. Each phase builds on the previous, adding new analysis capabilities.
