#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# H2N Bridge — ONE-TIME Qt Fix Script
# Run this once to fix "Could not find Qt platform plugin cocoa"
# ──────────────────────────────────────────────────────────────────────
echo "=== H2N Bridge Qt Fix ==="

PROJECT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$PROJECT_DIR"

# Find the venv
PYTHON_EXE=""
SITE_PACKAGES=""
for VENV_DIR in ".venv311" ".venv" "venv"; do
    if [ -x "$PROJECT_DIR/$VENV_DIR/bin/python" ]; then
        PYTHON_EXE="$PROJECT_DIR/$VENV_DIR/bin/python"
        SITE_PACKAGES="$PROJECT_DIR/$VENV_DIR/lib/python3.11/site-packages"
        PIP_EXE="$PROJECT_DIR/$VENV_DIR/bin/pip"
        break
    fi
done

if [ -z "$PYTHON_EXE" ]; then
    echo "ERROR: No virtualenv found in $PROJECT_DIR"
    exit 1
fi

echo "Found Python: $PYTHON_EXE"

# Check if cocoa plugin exists
PLUGIN_DIR="$SITE_PACKAGES/PyQt6/Qt6/plugins/platforms"
if [ -f "$PLUGIN_DIR/libqcocoa.dylib" ]; then
    echo "✅ Cocoa plugin already exists at $PLUGIN_DIR/libqcocoa.dylib"
    echo "The Qt installation is OK. Run ./run.sh to start the app."
    exit 0
fi

echo "❌ Cocoa plugin NOT found. Reinstalling PyQt6-Qt6..."
"$PIP_EXE" install --force-reinstall PyQt6-Qt6

# Verify
if [ -f "$PLUGIN_DIR/libqcocoa.dylib" ]; then
    echo ""
    echo "✅ Fix successful! Run ./run.sh to start the app."
else
    echo ""
    echo "❌ Still not found. Trying a full PyQt6 reinstall..."
    "$PIP_EXE" install --force-reinstall PyQt6 PyQt6-Qt6 PyQt6-sip
    if [ -f "$PLUGIN_DIR/libqcocoa.dylib" ]; then
        echo "✅ Fix successful! Run ./run.sh to start the app."
    else
        echo "❌ Could not fix automatically. Plugin dir contents:"
        ls -la "$PLUGIN_DIR" 2>/dev/null || echo "(directory does not exist)"
    fi
fi
