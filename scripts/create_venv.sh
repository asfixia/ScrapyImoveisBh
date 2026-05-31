#!/usr/bin/env bash
# One-time setup: create .venv and install project dependencies (Linux / macOS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
VENV_DIR=".venv"
VENV_PY="$VENV_DIR/bin/python"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Error: $PYTHON not found. Install Python 3.12+ or set PYTHON=python3.12"
  exit 1
fi

echo "Using: $("$PYTHON" --version) ($PYTHON)"

venv_pip_ok() {
  [ -x "$VENV_PY" ] && "$VENV_PY" -m pip --version >/dev/null 2>&1
}

if [ -d "$VENV_DIR/bin" ]; then
  if venv_pip_ok; then
    echo "Virtual environment already exists at $VENV_DIR"
    echo "Reinstall: rm -rf $VENV_DIR && ./create_venv.sh"
    exit 0
  fi
  echo "Incomplete $VENV_DIR (venv pip not available). Remove it and run again:"
  echo "  rm -rf $VENV_DIR && ./create_venv.sh"
  exit 1
fi

echo "Creating virtual environment in $VENV_DIR ..."
"$PYTHON" -m venv "$VENV_DIR"

if ! venv_pip_ok; then
  echo "Bootstrapping pip inside the venv (ensurepip) ..."
  "$VENV_PY" -m ensurepip --upgrade
fi

if ! venv_pip_ok; then
  echo ""
  echo "Error: pip is not available inside $VENV_DIR."
  echo "On Debian/Ubuntu install:"
  echo "  sudo apt install python3-venv python3-full"
  echo "Then: rm -rf $VENV_DIR && ./create_venv.sh"
  exit 1
fi

# Always use the venv interpreter — never system pip (PEP 668 on Debian/Ubuntu).
"$VENV_PY" -m pip install --upgrade pip wheel
"$VENV_PY" -m pip install -r requirements.txt

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
echo "  $VENV_PY -m playwright install chromium"
