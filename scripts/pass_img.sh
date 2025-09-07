#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   pass_img.sh <image_path> [csv_path] [run_log_path]
#
# Auto mode (only file given):
#   - /data/output/_adhoc/<stem>/<stem>.csv
#   - /data/output/_adhoc/<stem>/run.log
#
# Calls: pass_img.py <img> <csv> <run.log>

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
IMG_PATH="${1:-}"

if [[ -z "${IMG_PATH}" ]]; then
  echo "usage: $(basename "$0") <image_path> [csv_path] [run_log_path]" >&2
  exit 2
fi

if [[ ! -f "$IMG_PATH" ]]; then
  echo "error: not a file: $IMG_PATH" >&2
  exit 2
fi

STEM="$(basename "${IMG_PATH%.*}")"

CSV_PATH="${2:-}"
RUN_LOG="${3:-}"

if [[ -z "$CSV_PATH" || -z "$RUN_LOG" ]]; then
  OUT_BASE="/data/output/_adhoc/${STEM}"
  mkdir -p "$OUT_BASE"
  CSV_PATH="${CSV_PATH:-${OUT_BASE}/${STEM}.csv}"
  RUN_LOG="${RUN_LOG:-${OUT_BASE}/run.log}"
fi

python3 "${SCRIPT_DIR}/pass_img.py" "$IMG_PATH" "$CSV_PATH" "$RUN_LOG"
