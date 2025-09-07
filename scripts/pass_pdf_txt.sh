#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   pass_pdf_txt.sh <pdf_path> [csv_path] [run_log_path]
#
# Auto mode (only file given):
#   - /data/output/_adhoc/<stem>/<stem>_txtonly.csv
#   - /data/output/_adhoc/<stem>/run.log
#
# Note: This invokes the orchestrator (pass_pdf.py) which will escalate to OCR
# if TXT fails. For a pure TXT probe, pass a high OCR cutoffs via env (e.g.,
# PASS_OCR_A_CUTOFF=2 PASS_OCR_B_CUTOFF=2) so OCR never accepts.

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
  CSV_PATH="${CSV_PATH:-${OUT_BASE}/${STEM}_txtonly.csv}"
  RUN_LOG="${RUN_LOG:-${OUT_BASE}/run.log}"
fi

# Tip: set OCR cutoffs to 2 to effectively disable OCR for this probe:
#   PASS_OCR_A_CUTOFF=2 PASS_OCR_B_CUTOFF=2 scripts/pass_pdf_txt.sh <file.pdf>
python3 "${SCRIPT_DIR}/pass_pdf.py" "$PDF_PATH" "$CSV_PATH" "$RUN_LOG"
