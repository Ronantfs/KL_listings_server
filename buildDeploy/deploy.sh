#!/bin/bash
set -euo pipefail

# Resolve dirs
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment (.venv)"
  uv venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "Installing requirements into venv"
uv pip install -r "$PROJECT_DIR/requirements.txt"

python "$SCRIPT_DIR/deploy_lambda.py" "$@"
