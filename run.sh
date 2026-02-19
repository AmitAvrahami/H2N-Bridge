#!/bin/bash
# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Ensure we don't pick up the user's activated virtualenv (venv python 3.14)
unset VIRTUAL_ENV
export PATH="$DIR/.venv311/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if [ ! -d "$DIR/.venv311" ]; then
    echo "Error: Python environment '.venv311' not found in $DIR. Please create it or use 'setup.sh'."
    exit 1
fi

# Define paths for Qt plugins
PLUGINS="$DIR/.venv311/lib/python3.11/site-packages/PyQt6/Qt6/plugins"

# Export environment variables to help PyQt6 find its plugins.
# QT_PLUGIN_PATH points to the plugins root; Qt appends /platforms internally.
# Note: DYLD_FRAMEWORK_PATH is stripped by macOS SIP for child processes, so we omit it.
export QT_PLUGIN_PATH="$PLUGINS"
export QT_MAC_WANTS_LAYER=1       # Required for CALayer-backed views on macOS 13+
export PYTHONPATH="$DIR:$DIR/src"

echo "Starting H2N Bridge..."
if [ -z "$1" ]; then
    "$DIR/.venv311/bin/python" -m h2n_bridge.main
else
    # Check if the argument is a file or a module
    if [[ "$1" == *.py ]]; then
        "$DIR/.venv311/bin/python" "$1"
    else
        "$DIR/.venv311/bin/python" -m "$1"
    fi
fi
