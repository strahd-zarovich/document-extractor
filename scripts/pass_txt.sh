#!/usr/bin/env bash
set -Eeuo pipefail

# Args
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

log_debug "TXT ingestion starting: $file"

method="plain_text"
used_ocr=false
page_num=1
wrote_any=false

# Ensure file is readable; if not, fail
if [[ ! -r "$file" ]]; then
  log_warn "TXT not readable: $(basename "$file")"
  exit 1
fi

# Emit NON-BLANK lines only
while IFS= read -r line || [[ -n "$line" ]]; do
  # skip blank/whitespace-only lines
  [[ -z "${line//[[:space:]]/}" ]] && continue

  # CSV (RFC-4180: escape quotes by doubling)
  safe_csv="${line//\"/\"\"}"
  printf '"%s",%d,"%s"\n' "$file" "$page_num" "$safe_csv" >> "$csv"

  # JSONL (escape for JSON)
  safe_json="${line//\\/\\\\}"; safe_json="${safe_json//\"/\\\"}"
  printf '{"file":"%s","page":%d,"text":"%s","method":"%s","used_ocr":%s}\n' \
         "$file" "$page_num" "$safe_json" "$method" "$used_ocr" >> "$json"

  wrote_any=true
  ((page_num++))
done < "$file"

if [[ "$wrote_any" != true ]]; then
  log_warn "TXT contained only blank lines after cleaning: $(basename "$file")"
  exit 1
fi

log_debug "TXT ingestion completed: $file"
exit 0
