#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   pass_pdf.sh <pdf_path> [csv_path] [run_log_path]
#
# If only <pdf_path> is given, this wrapper will:
#   - create /data/output/_adhoc/<stem>/
#   - set CSV to   /data/output/_adhoc/<stem>/<stem>.csv
#   - set run.log to /data/output/_adhoc/<stem>/run.log
#
# It then calls the Python orchestrator: pass_pdf.py <pdf> <csv> <run.log>

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PDF_PATH="${1:-}"

if [[ -z "${PDF_PATH}" ]]; then
  echo "usage: $(basename "$0") <pdf_path> [csv_path] [run_log_path]" >&2
  exit 2
fi

if [[ ! -f "$PDF_PATH" ]]; then
  echo "error: not a file: $PDF_PATH" >&2
  exit 2
fi

STEM="$(basename "${PDF_PATH%.*}")"

CSV_PATH="${2:-}"
RUN_LOG="${3:-}"

if [[ -z "$CSV_PATH" || -z "$RUN_LOG" ]]; then
  OUT_BASE="/data/output/_adhoc/${STEM}"
  mkdir -p "$OUT_BASE"
  CSV_PATH="${CSV_PATH:-${OUT_BASE}/${STEM}.csv}"
  RUN_LOG="${RUN_LOG:-${OUT_BASE}/run.log}"
fi

python3 "${SCRIPT_DIR}/pass_pdf.py" "$PDF_PATH" "$CSV_PATH" "$RUN_LOG"
