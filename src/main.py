"""Entry point for the code-analyzer orchestrator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from orchestrator import main

if __name__ == "__main__":
    main()
