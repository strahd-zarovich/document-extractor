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

tmp_txt="$(mktemp -p "${WORK_DIR:-/tmp/work}" docx.XXXXXX.txt)"
method="docx_native"
used_ocr=false
wrote_any=false

log_debug "DOC/DOCX extraction starting: $file"

# Prefer docx2txt
if command -v docx2txt >/dev/null 2>&1; then
  docx2txt < "$file" > "$tmp_txt" 2>/dev/null || true
fi

# Fallback to LibreOffice headless
if [[ ! -s "$tmp_txt" ]]; then
  lo_out_dir="$(mktemp -d -p "${WORK_DIR:-/tmp/work}" lo.XXXXXX)"
  soffice --headless --convert-to txt:"Text" --outdir "$lo_out_dir" "$file" >/dev/null 2>&1 || true
  candidate="$(find "$lo_out_dir" -maxdepth 1 -type f -name '*.txt' | head -n1 || true)"
  if [[ -n "$candidate" && -s "$candidate" ]]; then
    mv "$candidate" "$tmp_txt"
    method="lo_txt"
  fi
  rm -rf "$lo_out_dir" 2>/dev/null || true
fi

# Image-heavy DOCX heuristic: if no text and many embedded images, bail
if [[ ! -s "$tmp_txt" && "${file,,}" == *.docx ]]; then
  if unzip -l "$file" 2>/dev/null | awk '{print $4}' | grep -q '^word/media/'; then
    log_warn "DOCX likely image-heavy; skipping to avoid OCR garbage: $(basename "$file")"
    rm -f "$tmp_txt"
    exit 1
  fi
fi

# Fail if no text at all
if [[ ! -s "$tmp_txt" ]]; then
  log_warn "DOC/DOCX extraction produced no text: $(basename "$file")"
  rm -f "$tmp_txt"
  exit 1
fi

# Emit NON-BLANK lines only
page_num=1
while IFS= read -r line || [[ -n "$line" ]]; do
  # skip blank/whitespace-only lines
  [[ -z "${line//[[:space:]]/}" ]] && continue

  # CSV (RFC-4180 escaping)
  safe_csv="${line//\"/\"\"}"
  printf '"%s",%d,"%s"\n' "$file" "$page_num" "$safe_csv" >> "$csv"

  # JSONL (escape)
  safe_json="${line//\\/\\\\}"; safe_json="${safe_json//\"/\\\"}"
  printf '{"file":"%s","page":%d,"text":"%s","method":"%s","used_ocr":%s}\n' \
         "$file" "$page_num" "$safe_json" "$method" "$used_ocr" >> "$json"

  wrote_any=true
  ((page_num++))
done < "$tmp_txt"

rm -f "$tmp_txt"

if [[ "$wrote_any" != true ]]; then
  log_warn "DOC/DOCX had only blank lines after cleaning: $(basename "$file")"
  exit 1
fi

log_debug "DOC/DOCX extraction completed: $file (method=${method})"
exit 0
