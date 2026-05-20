#!/usr/bin/env bash
# One-time setup: create .venv and install project dependencies (Linux / macOS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
VENV_DIR=".venv"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Error: $PYTHON not found. Install Python 3.12+ or set PYTHON=python3.12"
  exit 1
fi

echo "Using: $("$PYTHON" --version) ($PYTHON)"

if [ -d "$VENV_DIR/bin" ]; then
  echo "Virtual environment already exists at $VENV_DIR"
  echo "Reinstall: rm -rf $VENV_DIR && ./create_venv.sh"
  exit 0
fi

echo "Creating virtual environment in $VENV_DIR ..."
"$PYTHON" -m venv "$VENV_DIR"

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

pip install --upgrade pip wheel
pip install -r requirements.txt

mkdir -p output

echo ""
echo "Done."
echo "  Activate:  source ./activate_venv.sh"
echo "  Or:        source $VENV_DIR/bin/activate"
echo ""
echo "Examples:"
echo "  scrapy crawl NetImoveis"
echo "  scrapy crawl CasaMineira"
echo "  python zap_botasaurus_client.py"
echo ""
echo "Optional (only if you enable scrapy-playwright in settings):"
echo "  playwright install chromium"
