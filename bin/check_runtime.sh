#!/usr/bin/env bash
# yc-plugin runtime check — verify python3 is available before plugin runs.
# Exits 1 with install hints if missing. Stays silent when everything's fine.

set -e

if command -v python3 >/dev/null 2>&1; then
  exit 0
fi

cat >&2 <<'EOF'

[yc-plugin] python3 not found on PATH.

This plugin needs Python 3.10+ to run. Install it first:

  macOS:    brew install python@3.12
  Ubuntu:   sudo apt install python3 python3-pip
  Fedora:   sudo dnf install python3 python3-pip
  Windows:  https://www.python.org/downloads/  (check "Add to PATH")
  Other:    https://www.python.org/downloads/

After install, restart your shell and run /yc-plugin:youtube-setup again.

EOF

exit 1
