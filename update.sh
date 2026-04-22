#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
REQ_FILE="requirements.txt"

# Ensure virtualenv exists
if [[ ! -d "$VENV_DIR" ]]; then
    echo "[INFO] Creating virtual environment"
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

echo "[INFO] Fetching updates"
git fetch

# Capture current commit
OLD_COMMIT=$(git rev-parse HEAD)

# Pull changes
git pull

NEW_COMMIT=$(git rev-parse HEAD)

# No code change at all
if [[ "$OLD_COMMIT" == "$NEW_COMMIT" ]]; then
    echo "[INFO] No changes detected"
    exit 0
fi

# Check if requirements.txt changed
if git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" | grep -q "^$REQ_FILE$"; then
    echo "[INFO] requirements.txt changed – installing dependencies"
    pip install --upgrade pip
    pip install -r "$REQ_FILE"
else
    echo "[INFO] requirements.txt unchanged – skipping pip install"
fi
