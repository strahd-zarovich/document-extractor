#!/usr/bin/env bash
set -euo pipefail

# --- Config (override via env) ---
INPUT_DIR="${INPUT_DIR:-/data/input}"
PARENT_DISPOSITION="${PARENT_DISPOSITION:-hide}" # hide|leave
PUID="${PUID:-99}"
PGID="${PGID:-100}"
UMASK="${UMASK:-0002}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '%s %s\n' "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')]" "$*"; }

if ! command -v pdfdetach >/dev/null 2>&1; then
  echo "ERROR: pdfdetach not found (install poppler-utils)" >&2
  exit 1
fi

log "Portfolio unpacker: INPUT_DIR=$INPUT_DIR PARENT_DISPOSITION=$PARENT_DISPOSITION PUID=$PUID PGID=$PGID"

# Run the Python worker
exec python3 "$SCRIPT_DIR/portfolio_unpack.py" \
  --input "$INPUT_DIR" \
  --parent-disposition "$PARENT_DISPOSITION" \
  --puid "$PUID" --pgid "$PGID" --umask "$UMASK"
