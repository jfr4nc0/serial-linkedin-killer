#!/usr/bin/env python3
"""Entry point for the CLI interactive client."""

import sys
from pathlib import Path

# Ensure project root is in sys.path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.cli.client import JobApplicationCLI

if __name__ == "__main__":
    cli = JobApplicationCLI()
    cli.run()
