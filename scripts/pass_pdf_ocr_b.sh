#!/usr/bin/env bash
set -euo pipefail
: "${LOG_DIR:=/data/logs}"; mkdir -p "$LOG_DIR"
exec python3 /app/scripts/pass_pdf_ocr_b.py "$@" 2>>"$LOG_DIR/python_errors.log"