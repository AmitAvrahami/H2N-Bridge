#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# H2N Bridge — Foreground Launcher
# ──────────────────────────────────────────────────────────────────────
# This script is designed to be called from a macOS .app bundle or
# double-clicked directly. It activates the virtualenv and launches
# the Python application in the FOREGROUND so the PyQt6 overlay and
# AppKit hotkey listeners work correctly.
# ──────────────────────────────────────────────────────────────────────

# Resolve the project root (one level up from scripts/)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

# Activate the best available virtualenv
PYTHON_EXE=""
for VENV_DIR in ".venv311" ".venv" "venv"; do
    if [ -x "$DIR/$VENV_DIR/bin/python" ]; then
        unset VIRTUAL_ENV
        export PATH="$DIR/$VENV_DIR/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        PYTHON_EXE="$DIR/$VENV_DIR/bin/python"
        break
    fi
done

if [ -z "$PYTHON_EXE" ]; then
    echo "Warning: Local Python environment not found. Falling back to system python3."
    PYTHON_EXE=$(command -v python3)
fi

# Required environment variables
export QT_MAC_WANTS_LAYER=1
export PYTHONPATH="$DIR:$DIR/src"

echo "Starting H2N Bridge using python at $PYTHON_EXE"
echo "Project root: $DIR"

# Run in the foreground — this is critical for GUI + hotkeys
cd "$DIR"
TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 exec "$PYTHON_EXE" -m h2n_bridge.main
