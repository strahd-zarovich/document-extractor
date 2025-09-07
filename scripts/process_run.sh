#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   process_run.sh <run_dir> [output_dir] [run_log_path]
#
# If only <run_dir> is provided:
#   - derives run_name from the folder name
#   - output_dir = /data/output/_adhoc/<run_name>
#   - run_log    = /data/output/_adhoc/<run_name>/run.log
#
# Calls: process_run.py <run_dir> <output_dir> <run_log_path>

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
RUN_DIR="${1:-}"

if [[ -z "${RUN_DIR}" ]]; then
  echo "usage: $(basename "$0") <run_dir> [output_dir] [run_log_path]" >&2
  exit 2
fi

if [[ ! -d "$RUN_DIR" ]]; then
  echo "error: not a directory: $RUN_DIR" >&2
  exit 2
fi

RUN_NAME="$(basename "$RUN_DIR")"

OUT_DIR="${2:-}"
RUN_LOG="${3:-}"

if [[ -z "$OUT_DIR" || -z "$RUN_LOG" ]]; then
  OUT_BASE="/data/output/_adhoc/${RUN_NAME}"
  mkdir -p "$OUT_BASE"
  OUT_DIR="${OUT_DIR:-${OUT_BASE}}"
  RUN_LOG="${RUN_LOG:-${OUT_BASE}/run.log}"
fi

python3 "${SCRIPT_DIR}/process_run.py" "$RUN_DIR" "$OUT_DIR" "$RUN_LOG"
