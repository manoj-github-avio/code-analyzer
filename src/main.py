"""Entry point — delegates to orchestrator_command for full argument handling."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from commands.orchestrator_command import main

if __name__ == "__main__":
    main()
