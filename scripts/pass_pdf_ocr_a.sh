#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   pass_pdf_ocr_a.sh <pdf_path> [csv_path] [run_log_path]
#
# What this does:
#   - Calls the orchestrator but *disables* TXT acceptance and OCR-B acceptance
#     by setting cutoffs so high they can’t pass:
#       PASS_TXT_CUTOFF=2   -> TXT never accepts
#       PASS_OCR_B_CUTOFF=2 -> OCR-B never accepts
#   - So only OCR-A can accept; if it fails, the whole run fails (good for probing)
#
# Auto mode (only file given):
#   - /data/output/_adhoc/<stem>/<stem>_ocr_a.csv
#   - /data/output/_adhoc/<stem>/run.log

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
  CSV_PATH="${CSV_PATH:-${OUT_BASE}/${STEM}_ocr_a.csv}"
  RUN_LOG="${RUN_LOG:-${OUT_BASE}/run.log}"
fi

# Force “OCR-A only”
PASS_TXT_CUTOFF=2 PASS_OCR_B_CUTOFF=2 \
python3 "${SCRIPT_DIR}/pass_pdf.py" "$PDF_PATH" "$CSV_PATH" "$RUN_LOG"
