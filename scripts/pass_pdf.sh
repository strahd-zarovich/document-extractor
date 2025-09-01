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

# --- Local knobs (pass-owned) ---
PDF_OCR_THRESHOLD=${PDF_OCR_THRESHOLD:-25}  # characters; below this per-page we OCR
OCR_DPI=${OCR_DPI:-300}
TESS_LANG=${TESS_LANG:-eng}
TESS_PSM=${TESS_PSM:-3}
TESS_OEM=${TESS_OEM:-1}

work_root="${WORK_DIR:-/tmp/work}"
work_dir="$(mktemp -d -p "$work_root" pdf.XXXXXX)"
trap 'rm -rf "$work_dir"' EXIT

log_debug "PDF extraction starting: $file"

# Page count & size (Option C)
pages=$(pdfinfo "$file" 2>/dev/null | awk -F': *' '/^Pages:/ {print $2}' | tr -d ' ' || true)
pages=${pages:-0}
size_bytes=$(stat -c%s "$file" 2>/dev/null || echo 0)
size_mb=$(( (size_bytes + 1024*1024 - 1) / (1024*1024) ))

# Decide if we write a page index CSV
bigpdf=false
if { [[ -n "${BIGPDF_PAGE_LIMIT:-}" && "$pages" -gt "${BIGPDF_PAGE_LIMIT}" ]] || [[ -n "${BIGPDF_SIZE_LIMIT_MB:-}" && "$size_mb" -gt "${BIGPDF_SIZE_LIMIT_MB}" ]]; }; then
  bigpdf=true
  base="$(basename "$file")"
  slug="${base%.*}"
  page_index_csv="${out_path}/${slug}.pages.csv"
  [[ -f "$page_index_csv" ]] || echo "page,chars,method,used_ocr,notes" > "$page_index_csv"
fi

# Fallback if pdfinfo failed
[[ "$pages" -eq 0 ]] && pages=1

wrote_any=false

for ((p=1; p<=pages; p++)); do
  page_txt="${work_dir}/p${p}.txt"
  notes="-"
  method="pdftext"
  used_ocr=false

  # Native text per page
  if ! pdftotext -f "$p" -l "$p" "$file" "$page_txt" 2>/dev/null; then
    : > "$page_txt"
  fi

  # Char count
  char_count=0
  [[ -f "$page_txt" ]] && char_count=$(wc -m < "$page_txt" | tr -d ' ')

  # OCR if too little native text
  if [[ "$char_count" -lt "$PDF_OCR_THRESHOLD" ]]; then
    ppm_prefix="${work_dir}/page-${p}"
    if pdftoppm -r "$OCR_DPI" -f "$p" -l "$p" "$file" "$ppm_prefix" >/dev/null 2>&1; then
      for ppm in "${ppm_prefix}"-*.ppm; do
        [[ -f "$ppm" ]] || continue
        tesseract "$ppm" "${ppm%.ppm}" -l "$TESS_LANG" --oem "$TESS_OEM" --psm "$TESS_PSM" >/dev/null 2>&1 || true
        [[ -f "${ppm%.ppm}.txt" ]] && cat "${ppm%.ppm}.txt" > "$page_txt"
        rm -f "${ppm%.ppm}.txt" "$ppm" 2>/dev/null || true
        break
      done
      used_ocr=true
      method="ocr_tesseract"
      notes="dpi=${OCR_DPI}; oem=${TESS_OEM}; psm=${TESS_PSM}"
    fi
    [[ -f "$page_txt" ]] && char_count=$(wc -m < "$page_txt" | tr -d ' ')

    # Fallback: MuPDF text stream
    if [[ "$char_count" -lt "$PDF_OCR_THRESHOLD" ]]; then
      mutool draw -F txt -o "${work_dir}/p${p}.mutxt" "$file" "$p" >/dev/null 2>&1 || true
      if [[ -s "${work_dir}/p${p}.mutxt" ]]; then
        mv -f "${work_dir}/p${p}.mutxt" "$page_txt"
        char_count=$(wc -m < "$page_txt" | tr -d ' ')
        used_ocr=true
        method="ocr_mupdf"
        notes="mutool txt"
      fi
    fi
  fi

  # Write outputs for NON-BLANK lines only
  if [[ -s "$page_txt" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      # skip blank/whitespace-only lines
      [[ -z "${line//[[:space:]]/}" ]] && continue

      # CSV (RFC-4180: escape quotes by doubling)
      safe_csv="${line//\"/\"\"}"
      printf '"%s",%d,"%s"\n' "$file" "$p" "$safe_csv" >> "$csv"

      # JSONL (escape for JSON)
      safe_json="${line//\\/\\\\}"; safe_json="${safe_json//\"/\\\"}"
      printf '{"file":"%s","page":%d,"text":"%s","method":"%s","used_ocr":%s}\n' \
             "$file" "$p" "$safe_json" "$method" "$used_ocr" >> "$json"

      wrote_any=true
    done < "$page_txt"
  fi

  # Page index for big PDFs
  if [[ "$bigpdf" == true ]]; then
    printf '%d,%d,%s,%s,"%s"\n' "$p" "$char_count" "$method" "$used_ocr" "$notes" >> "$page_index_csv"
  fi
done

# Success only if we wrote at least one non
