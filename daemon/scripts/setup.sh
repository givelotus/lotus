#!/usr/bin/env bash
# Initialize pinned submodules only. Stack application is a separate reviewed step.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -gt 0 || -n "${RESET:-}" ]]; then
    echo "Setup preserves source checkouts; RESET and replay arguments are unsupported." >&2
    exit 1
fi
exec python3 "$SCRIPT_DIR/daemon_sources.py" setup "${SERIES:-v1}"
