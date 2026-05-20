#!/usr/bin/env bash
# Activate the project venv in your current shell.
# Usage:  source ./activate_venv.sh

_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

if [ -n "${BASH_VERSION:-}" ] && [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  echo "Run with source, not execute:"
  echo "  source ./activate_venv.sh"
  exit 1
fi

if [ ! -f "$_ROOT/.venv/bin/activate" ]; then
  echo "Virtual environment not found. Run first: ./create_venv.sh"
  return 1 2>/dev/null || exit 1
fi

# shellcheck source=/dev/null
source "$_ROOT/.venv/bin/activate"
cd "$_ROOT"
echo "Venv activated ($(python --version)). Project root: $_ROOT"
