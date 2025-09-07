#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   pass_any.sh <file> [csv_path] [run_log_path]
#
# Routes by extension:
#   .pdf  -> pass_pdf.py (full TXT -> OCR-A -> OCR-B chain)
#   .docx -> pass_doc.py
#   .doc  -> pass_doc.py
#   .txt  -> pass_txt.py
#   .tif/.tiff/.png/.jpg/.jpeg -> pass_img.py
#
# Auto mode (only file given):
#   - /data/output/_adhoc/<stem>/<stem>.csv
#   - /data/output/_adhoc/<stem>/run.log

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
FILE="${1:-}"

if [[ -z "${FILE}" ]]; then
  echo "usage: $(basename "$0") <file> [csv_path] [run_log_path]" >&2
  exit 2
fi
if [[ ! -f "$FILE" ]]; then
  echo "error: not a file: $FILE" >&2
  exit 2
fi

STEM="$(basename "${FILE%.*}")"
EXT_LOWER=".${FILE##*.}"
EXT_LOWER="${EXT_LOWER,,}"

CSV_PATH="${2:-}"
RUN_LOG="${3:-}"

if [[ -z "$CSV_PATH" || -z "$RUN_LOG" ]]; then
  OUT_BASE="/data/output/_adhoc/${STEM}"
  mkdir -p "$OUT_BASE"
  CSV_PATH="${CSV_PATH:-${OUT_BASE}/${STEM}.csv}"
  RUN_LOG="${RUN_LOG:-${OUT_BASE}/run.log}"
fi

case "$EXT_LOWER" in
  .pdf)   TARGET="pass_pdf.py" ;;
  .docx|.doc) TARGET="pass_doc.py" ;;
  .txt)   TARGET="pass_txt.py" ;;
  .tif|.tiff|.png|.jpg|.jpeg) TARGET="pass_img.py" ;;
  *)
    echo "unsupported extension: $EXT_LOWER" >&2
    exit 2
  ;;
esac

python3 "${SCRIPT_DIR}/${TARGET}" "$FILE" "$CSV_PATH" "$RUN_LOG"
