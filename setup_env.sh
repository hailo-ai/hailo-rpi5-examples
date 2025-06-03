#!/usr/bin/env bash

# Only proceed if the script is being sourced
is_sourced() {
    # Works in bash and zsh
    [[ "${BASH_SOURCE[0]}" != "$0" ]]
}

if ! is_sourced; then
    echo "⚠️ Please source this script, not execute it:"
    echo "   source $(basename "$0")"
    return 1
fi

echo "🔧 Setting up environment..."

# Look for *any* venv directory in the current folder
# (you can restrict the pattern if you want a specific name, e.g. venv*)
for d in ./venv*; do
    if [ -d "$d/bin" ] && [ -f "$d/bin/activate" ]; then
        VENV_DIR="$d"
        break
    fi
done

if [ -n "${VENV_DIR:-}" ]; then
    if [ "$VIRTUAL_ENV" = "$PWD/${VENV_DIR#./}" ]; then
        echo "✅ Already in virtualenv '$VENV_DIR'."
    else
        echo "🔀 Activating existing virtualenv '$VENV_DIR'..."
        # shellcheck disable=SC1091
        source "$VENV_DIR/bin/activate"
        echo "🐍 Virtualenv activated: $VIRTUAL_ENV"
    fi
else
    echo "⚠️ No virtualenv found in $(pwd). Skipping activation."
fi