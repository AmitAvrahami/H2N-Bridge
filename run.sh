#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 1. מציאת הסביבה הוירטואלית
PYTHON_EXE=""
VENV_PATH=""
for VENV_DIR in ".venv311" ".venv" "venv"; do
    if [ -x "$DIR/$VENV_DIR/bin/python" ]; then
        unset VIRTUAL_ENV
        export PATH="$DIR/$VENV_DIR/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        PYTHON_EXE="$DIR/$VENV_DIR/bin/python"
        VENV_PATH="$DIR/$VENV_DIR"
        break
    fi
done

if [ -z "$PYTHON_EXE" ]; then
    echo "Warning: Local Python environment not found. Falling back to system python3."
    PYTHON_EXE=$(command -v python3)
fi

# 2. הגדרות מערכת ל-macOS
export QT_MAC_WANTS_LAYER=1
export PYTHONPATH="$DIR:$DIR/src"
export QT_QPA_PLATFORM=cocoa

# 3. חיפוש דינמי של ה-Plugins (תומך ב-Python 3.14)
# הפקודה הזו מוצאת את התיקייה לא משנה מה מספר הגרסה
QT_PLUGIN_CANDIDATE=$(find "$VENV_PATH/lib" -name "plugins" -type d -path "*/PyQt6/Qt6/plugins" 2>/dev/null | head -n 1)

if [ -n "$QT_PLUGIN_CANDIDATE" ]; then
    export QT_PLUGIN_PATH="$QT_PLUGIN_CANDIDATE"
    export QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PLUGIN_CANDIDATE/platforms"
    echo "✅ Found Qt plugins at: $QT_PLUGIN_PATH"
else
    echo "⚠️ Warning: Could not find Qt plugins in $VENV_PATH"
fi

echo "Starting H2N Bridge using python at $PYTHON_EXE"

# 4. הרצת האפליקציה
if [ -z "$1" ]; then
    TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 "$PYTHON_EXE" -m h2n_bridge.main
else
    if [[ "$1" == *.py ]]; then
        "$PYTHON_EXE" "$1"
    else
        "$PYTHON_EXE" -m "$1"
    fi
fi