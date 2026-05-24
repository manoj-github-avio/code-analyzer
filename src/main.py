"""Entry point — delegates to the CLI orchestrator subcommand."""
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    sys.argv.insert(1, "orchestrator")
    from cli import cli
    cli()
