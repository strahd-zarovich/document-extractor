#!/usr/bin/env bash
set -euo pipefail

# Read env (with safe defaults)
INPUT_DIR="${INPUT_DIR:-/data/input}"
PARENT_DISPOSITION="${PARENT_DISPOSITION:-hide}"
PUID="${PUID:-99}"
PGID="${PGID:-100}"
UMASK="${UMASK:-0002}"
WORK_DIR="${WORK_DIR:-/data/tmp}"   # NEW: default /data/tmp

# Delegate to Python worker
exec /usr/bin/env python3 /app/scripts/portfolio_unpack.py \
  --input "$INPUT_DIR" \
  --parent-disposition "$PARENT_DISPOSITION" \
  --puid "$PUID" \
  --pgid "$PGID" \
  --umask "$UMASK" \
  --workdir "$WORK_DIR"
