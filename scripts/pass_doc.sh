#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   pass_doc.sh <doc_or_docx_path> [csv_path] [run_log_path]
#
# Auto mode (only file given):
#   - /data/output/_adhoc/<stem>/<stem>.csv
#   - /data/output/_adhoc/<stem>/run.log

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
DOC_PATH="${1:-}"

if [[ -z "${DOC_PATH}" ]]; then
  echo "usage: $(basename "$0") <doc|docx_path> [csv_path] [run_log_path]" >&2
  exit 2
fi

if [[ ! -f "$DOC_PATH" ]]; then
  echo "error: not a file: $DOC_PATH" >&2
  exit 2
fi

STEM="$(basename "${DOC_PATH%.*}")"

CSV_PATH="${2:-}"
RUN_LOG="${3:-}"

if [[ -z "$CSV_PATH" || -z "$RUN_LOG" ]]; then
  OUT_BASE="/data/output/_adhoc/${STEM}"
  mkdir -p "$OUT_BASE"
  CSV_PATH="${CSV_PATH:-${OUT_BASE}/${STEM}.csv}"
  RUN_LOG="${RUN_LOG:-${OUT_BASE}/run.log}"
fi

python3 "${SCRIPT_DIR}/pass_doc.py" "$DOC_PATH" "$CSV_PATH" "$RUN_LOG"
