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

# Check kernel version
check_kernel_version() {
    MAX_VERSION="6.12.25"
    CURRENT_VERSION=$(uname -r | cut -d '+' -f 1) # Extract numeric version part

    # Check if CURRENT_VERSION is greater than or equal to MAX_VERSION
    if [[ "$(printf '%s\n' "$CURRENT_VERSION" "$MAX_VERSION" | sort -V | tail -n1)" == "$CURRENT_VERSION" ]]; then
        echo "Error: Kernel version $CURRENT_VERSION detected. This version is incompatible."
        echo "Please refer to the following link for more information:"
        echo "https://community.hailo.ai/t/raspberry-pi-kernel-compatibility-issue-temporary-fix/15322"
        return 1
    fi
}

echo "Checking kernel version..."
# Call the kernel version check function
check_kernel_version || {
    echo "Exiting due to incompatible kernel version."
    return 1
}

echo "🔧 Setting up environment..."

# Look for any directory in the current folder that contains bin/activate
for d in ./*; do
    if [ -d "$d" ] && [ -f "$d/bin/activate" ]; then
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