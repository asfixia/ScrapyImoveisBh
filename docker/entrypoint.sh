#!/bin/sh
set -e

export SCRAPE_OUTPUT_DIR="${SCRAPE_OUTPUT_DIR:-/data}"
mkdir -p "$SCRAPE_OUTPUT_DIR" /app/logs

exec python -u /app/main_update_data.py
