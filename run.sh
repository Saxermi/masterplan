#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  exec python3 server.py "$@"
fi
printf '%s\n' 'Python 3.10 or later is required. Install Python and run again.' >&2
exit 1
