"""Merge latest scraped JSON files. Superseded by pipeline/merge.py — kept for manual use."""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

subprocess.run(
    [sys.executable, str(PROJECT_ROOT / "pipeline" / "merge.py")],
    cwd=PROJECT_ROOT,
    check=True,
)
