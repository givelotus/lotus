#!/bin/bash
# Keep Xcode selection local, including Dart native hooks that filter environment.
set -euo pipefail
export DEVELOPER_DIR="${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}"
if [[ ! -d "$DEVELOPER_DIR" || $# -eq 0 ]]; then
  echo 'Usage: DEVELOPER_DIR=/path/to/Xcode.app/Contents/Developer tool/with_xcode.sh <command> [args...]' >&2
  exit 2
fi
lotus_xcode_tools=$(mktemp -d "${TMPDIR:-/tmp}/lotus-xcode-tools.XXXXXX")
trap 'rm -f "$lotus_xcode_tools/xcrun"; rmdir "$lotus_xcode_tools"' EXIT
# hooks_runner forwards PATH but filters DEVELOPER_DIR. The wrapper preserves the
# explicitly selected SDK without changing this Mac's global xcode-select setting.
printf '#!/bin/bash\nexport DEVELOPER_DIR=%q\nexec /usr/bin/xcrun "$@"\n' "$DEVELOPER_DIR" > "$lotus_xcode_tools/xcrun"
chmod +x "$lotus_xcode_tools/xcrun"
export PATH="$lotus_xcode_tools:$PATH"
"$@"
