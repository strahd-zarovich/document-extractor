#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   pass_pdf_ocr_b.sh <pdf_path> [csv_path] [run_log_path]
#
# What this does:
#   - Disables TXT and OCR-A acceptance, so the orchestrator goes straight to OCR-B
#     (TXT never accepts; OCR-A never accepts).
#       PASS_TXT_CUTOFF=2
#       PASS_OCR_A_CUTOFF=2
#   - OCR-B can accept normally at its configured cutoff.
#
# Auto mode (only file given):
#   - /data/output/_adhoc/<stem>/<stem>_ocr_b.csv
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
  CSV_PATH="${CSV_PATH:-${OUT_BASE}/${STEM}_ocr_b.csv}"
  RUN_LOG="${RUN_LOG:-${OUT_BASE}/run.log}"
fi

# Force “OCR-B only”
PASS_TXT_CUTOFF=2 PASS_OCR_A_CUTOFF=2 \
python3 "${SCRIPT_DIR}/pass_pdf.py" "$PDF_PATH" "$CSV_PATH" "$RUN_LOG"
