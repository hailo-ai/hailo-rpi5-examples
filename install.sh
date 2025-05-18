#!/usr/bin/env bash
set -euo pipefail

# Navigate to the script’s directory so relative paths in install.py work
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  -c, --config <path>       Path to the RPI examples config file
                            (default: config/config.yaml)
  -h, --help                Show this help message and exit

All other arguments are passed straight through to install.py.
For example, if your config.yaml enables infra-download flags like:
    --all
    --group <group_name>
    --resources-config <file>
you can include them here and they’ll be forwarded to the Hailo Apps Infra installer.

Examples:
  $0 --config custom.yaml
  $0 -c configs/mycfg.yaml --all
EOF
}

# If the user asked for help, show usage and exit
if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
  usage
  exit 0
fi

# Show the user exactly what args we're forwarding
if [ $# -eq 0 ]; then
  echo "🔧 No arguments provided; running install.py with defaults."
else
  echo "🔧 Forwarding to install.py: $*"
fi

# Replace the shell with the Python installer, passing all flags through
exec python3 install.py "$@"
