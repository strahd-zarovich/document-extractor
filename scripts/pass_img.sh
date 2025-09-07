#!/usr/bin/env bash
# pass_img.sh — Standalone image OCR (CSV-only)
# Args: <file> <csv_out> <json_out> <out_dir>
set -Eeuo pipefail

file="$1"
csv="$2"
json="$3"  # unused
out_dir="$4"

[[ -n "${CONFIG_FILE:-}" && -f "${CONFIG_FILE}" ]] && . "${CONFIG_FILE}"
# shellcheck disable=SC1091
. /app/scripts/common.sh

IMG_MIN_CHARS=80

# Ensure run CSV header exists
if [[ -n "${csv:-}" && ! -s "$csv" ]]; then
  printf 'filename,page,text,method,used_ocr\n' > "$csv"
fi

clean_text() { sed 's/\r//g' | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/"/""/g'; }
count_chars() { printf '%s' "$1" | tr -d '\n\r\t ' | wc -c | awk '{print $1}'; }

bn="$(basename -- "$file")"

if ! command -v tesseract >/dev/null 2>&1; then
  log_error "tesseract not available for image OCR: $bn"; exit 1
fi

txt="$(tesseract "$file" stdout -l eng --oem 1 --psm 6 -c tessedit_do_invert=1 2>/dev/null || true)"
cleaned="$(printf '%s' "$txt" | clean_text)"
c="$(count_chars "$cleaned")"

if (( c < IMG_MIN_CHARS )); then
  # retry with psm 3
  txt="$(tesseract "$file" stdout -l eng --oem 1 --psm 3 -c tessedit_do_invert=1 2>/dev/null || true)"
  cleaned="$(printf '%s' "$txt" | clean_text)"
  c="$(count_chars "$cleaned")"
fi

if (( c < IMG_MIN_CHARS )); then
  log_warn "Image OCR produced too little text ($c): $bn"
  exit 1
fi

printf '"%s",1,"%s","%s",%s\n' "$file" "$cleaned" "img_ocr" true >> "$csv"
log_info "Image OCR complete: $bn (chars=$c)"
exit 0
