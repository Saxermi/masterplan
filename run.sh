#!/bin/sh
# POSIX launcher: both `sh run.sh` and `bash run.sh` are supported.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

# A partial ZIP extraction or deleted/Trash directory should not crash with a
# Python traceback at import time.
for required in server.py vvz_dump.py web/index.html guidelines/cse-guidelines.json; do
  if [ ! -f "$required" ]; then
    printf 'MasterPlan: required project file is missing: %s\n' "$required" >&2
    printf '%s\n' 'Your local copy appears incomplete (for example, a folder copied from Trash).' \
      'Download or clone the complete repository into a normal folder:' \
      '  git clone https://github.com/Saxermi/masterplan.git ~/masterplan-clean' \
      'Then run: cd ~/masterplan-clean && sh run.sh' >&2
    exit 1
  fi
done

python_compatible() {
  command -v "$1" >/dev/null 2>&1 &&
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

# Explicit override for users whose Conda installation makes python3 be 3.9.
if [ -n "${MASTERPLAN_PYTHON:-}" ]; then
  if python_compatible "$MASTERPLAN_PYTHON"; then
    exec "$MASTERPLAN_PYTHON" server.py "$@"
  fi
  printf 'MasterPlan: MASTERPLAN_PYTHON=%s is not a working Python 3.10+ interpreter.\n' "$MASTERPLAN_PYTHON" >&2
  exit 1
fi

# First prefer python3, then known versioned commands if python3 is too old.
for candidate in python3 python3.14 python3.13 python3.12 python3.11 python3.10; do
  if python_compatible "$candidate"; then
    exec "$candidate" server.py "$@"
  fi
done

printf '%s\n' 'MasterPlan requires Python 3.10 or newer.' \
  'Your current `python3` may point to an older Conda environment.' \
  'Check: python3 --version; command -v python3' \
  'Try: conda deactivate' \
  'Or select a compatible interpreter: MASTERPLAN_PYTHON=python3.12 sh run.sh' >&2
exit 1
