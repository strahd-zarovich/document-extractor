#!/usr/bin/env bash
# pass_txt.sh — normalize plain text files into the run CSV (no TXT artifacts)
# Args: <file> <csv_out> <json_out> <out_dir>
set -Eeuo pipefail

file="$1"
csv="$2"
json="$3"   # unused (signature preserved)
out_dir="$4"

# Load config & logging (if present)
[[ -n "${CONFIG_FILE:-}" && -f "${CONFIG_FILE}" ]] && . "${CONFIG_FILE}"
# shellcheck disable=SC1091
. /app/scripts/common.sh

# Ensure run CSV header exists (runner should have created it, but be safe)
if [[ -n "${csv:-}" && ! -s "$csv" ]]; then
  printf 'filename,page,text,method,used_ocr\n' > "$csv"
fi

# Helpers
clean_text() { sed 's/\r//g' | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/"/""/g'; }
count_chars() { printf '%s' "$1" | tr -d '\n\r\t ' | wc -c | awk '{print $1}'; }

bn="$(basename -- "$file")"

# Read file (handle large inputs via streaming)
if ! cleaned="$(cat -- "$file" | clean_text)"; then
  log_warn "Failed to read TXT: $bn"
  exit 1
fi

chars="$(count_chars "$cleaned")"
if (( chars < 20 )); then
  log_warn "TXT produced too little text ($chars): $bn"
  exit 1
fi

# Write a single 5-column row; txt is not OCR
printf '"%s",%d,"%s","%s",%s\n' "$file" 1 "$cleaned" "txt" false >> "$csv"
log_info "TXT normalized to CSV: $bn (chars=$chars)"
exit 0
