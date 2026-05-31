"""Shared JSON output paths for crawlers.

Default output folder is PROJECT_ROOT/output/.
Override at runtime with SCRAPE_OUTPUT_DIR for Docker / CI.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"


def output_dir() -> Path:
    raw = os.environ.get("SCRAPE_OUTPUT_DIR", "").strip()
    if raw:
        path = Path(raw)
        path.mkdir(parents=True, exist_ok=True)
        return path
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def output_json_path(site_name: str) -> Path:
    """e.g. 2026-05-13_01-48_casamineira.json under output_dir()."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return output_dir() / f"{stamp}_{site_name}.json"
