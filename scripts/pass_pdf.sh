#!/usr/bin/env bash
# pass_pdf.sh — PDF text + OCR (CSV-only; no TXT artifacts)
# Args: <file> <csv_out> <json_out> <out_dir>
set -Eeuo pipefail

file="$1"
csv="$2"
json="$3"
out_path="$4"

# Runtime config & logging
if [[ -n "${CONFIG_FILE:-}" && -f "${CONFIG_FILE}" ]]; then
  # shellcheck disable=SC1090
  . "${CONFIG_FILE}"
fi
# shellcheck disable=SC1091
. /app/scripts/common.sh

: "${WORK_DIR:=/tmp/work}"
: "${OCR_LANG:=eng}"
: "${PDF_TEXT_MIN_CHARS:=120}"
: "${PDF_OCR_DPI:=300}"
: "${WRITE_TXT_ARTIFACTS:=false}"   # must remain false per requirements

bn="$(basename -- "$file")"

work_dir="$(mktemp -d -p "${WORK_DIR}" "pdf.$$.$(date +%s).XXXX")"
trap 'rm -rf "$work_dir"' EXIT

txt_fast="${work_dir}/fast.txt"
txt_ocr="${work_dir}/ocr.txt"

# Ensure CSV header exists
if [[ -n "${csv:-}" && ! -s "$csv" ]]; then
  printf 'file,page,text,method,used_ocr\n' > "$csv"
fi

# 1) Try text layer first (pdftotext -layout)
if command -v pdftotext >/dev/null 2>&1; then
  if pdftotext -layout "$file" "$txt_fast" 2>/dev/null; then
    chars="$(tr -d '\n\r\t ' < "$txt_fast" | wc -c | awk '{print $1}')"
    if [[ "$chars" -ge "$PDF_TEXT_MIN_CHARS" ]]; then
      log_info "PDF text layer used: $bn (${chars} chars)"
      # Append one CSV row for entire PDF (compact; minimal change)
      if [[ -n "${csv:-}" ]]; then
        _t="$(sed 's/\r//g' "$txt_fast" | sed ':a;N;$!ba;s/\n/\\n/g')"
        _t="${_t//\"/\"\"}"
        printf '"%s",%d,"%s","%s",%s\n' "$file" 1 "$_t" "pdf_text" false >> "$csv"
      fi
      exit 0
    else
      log_debug "PDF text layer too small (${chars} < ${PDF_TEXT_MIN_CHARS}): $bn"
    fi
  else
    log_debug "pdftotext failed on: $bn"
  fi
else
  log_warn "pdftotext not found; skipping fast text for: $bn"
fi

# 2) OCR fallback (pdftoppm -> tesseract)
if ! command -v tesseract >/dev/null 2>&1; then
  log_error "tesseract not available; cannot OCR: $bn"
  exit 1
fi
if ! command -v pdftoppm >/dev/null 2>&1; then
  log_error "pdftoppm not available; cannot render for OCR: $bn"
  exit 1
fi

log_info "PDF OCR path: $bn (dpi=${PDF_OCR_DPI}, lang=${OCR_LANG})"

pdftoppm -r "$PDF_OCR_DPI" "$file" "${work_dir}/page" 1>/dev/null

> "$txt_ocr"
shopt -s nullglob
for ppm in "${work_dir}"/page-*.ppm; do
  base="${ppm%.*}"
  if tesseract "$ppm" "${base}" -l "$OCR_LANG" --psm 3 1>/dev/null 2>&1; then
    page_txt="${base}.txt"
    if [[ -s "$page_txt" ]]; then
      cat "$page_txt" >> "$txt_ocr"
      printf '\n' >> "$txt_ocr"
    fi
  else
    log_debug "tesseract failed on: ${ppm##*/}"
  fi
done

# Success only if we wrote useful text
if [[ -s "$txt_ocr" ]]; then
  chars="$(tr -d '\n\r\t ' < "$txt_ocr" | wc -c | awk '{print $1}')"
  if [[ "$chars" -ge "$PDF_TEXT_MIN_CHARS" ]]; then
    log_info "PDF OCR complete: $bn (${chars} chars)"
    if [[ -n "${csv:-}" ]]; then
      _t="$(sed 's/\r//g' "$txt_ocr" | sed ':a;N;$!ba;s/\n/\\n/g')"
      _t="${_t//\"/\"\"}"
      printf '"%s",%d,"%s","%s",%s\n' "$file" 1 "$_t" "ocr" true >> "$csv"
    fi
    exit 0
  fi
fi

log_warn "PDF produced too little text after OCR: $bn"
exit 1
