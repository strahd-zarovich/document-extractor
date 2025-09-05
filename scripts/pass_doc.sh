#!/usr/bin/env bash
# pass_doc.sh — DOC/DOCX handling (CSV-only; no TXT artifacts)
# Args: <file> <csv_out> <json_out> <out_dir>
set -Eeuo pipefail

file="$1"
csv="$2"   # run-level CSV to append to
json="$3"  # kept for signature; not used here
out_dir="$4"

# Load config & helpers if present
if [[ -n "${CONFIG_FILE:-}" && -f "${CONFIG_FILE}" ]]; then
  # shellcheck disable=SC1090
  . "${CONFIG_FILE}"
fi
# shellcheck disable=SC1091
. /app/scripts/common.sh

: "${WRITE_TXT_ARTIFACTS:=false}"   # must remain false per requirements

bn="$(basename -- "$file")"
ext="${bn##*.}"
ext_lc="$(printf '%s' "$ext" | tr 'A-Z' 'a-z')"

# Legacy .doc unsupported without LibreOffice -> let caller route to Manual Review
if [[ "$ext_lc" == "doc" ]]; then
  log_warn "Legacy .doc not supported without LibreOffice: $bn"
  exit 1
fi

if [[ "$ext_lc" != "docx" ]]; then
  log_warn "Unsupported extension for pass_doc: $bn"
  exit 1
fi

# Extract DOCX full text (body, tables, headers/footers, foot/endnotes, comments)
tmp_txt="$(mktemp -t docx_alltext.XXXXXX)"
trap 'rm -f "$tmp_txt"' EXIT

if ! command -v python3 >/dev/null 2>&1; then
  log_error "python3 not available for DOCX extraction: $bn"
  exit 1
fi

if ! python3 - "$file" > "$tmp_txt" 2>/dev/null <<'PY'
import sys, zipfile, xml.etree.ElementTree as ET
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

def text_from_part(xml_bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return []
    lines = []
    for p in root.findall('.//w:p', NS):
        segs = [t.text or "" for t in p.findall('.//w:t', NS)]
        s = "".join(segs).strip()
        if s:
            lines.append(s)
    return lines

def collect(path):
    out = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        parts = []
        if 'word/document.xml' in names:
            parts.append('word/document.xml')
        for n in sorted(names):
            if n.startswith('word/header') and n.endswith('.xml'):
                parts.append(n)
            elif n.startswith('word/footer') and n.endswith('.xml'):
                parts.append(n)
        for p in ('word/footnotes.xml','word/endnotes.xml','word/comments.xml'):
            if p in names:
                parts.append(p)
        for name in parts:
            try:
                lines = text_from_part(z.read(name))
                if lines:
                    if out: out.append("")
                    out.extend(lines)
            except Exception:
                pass
    return out

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(2)
    for line in collect(sys.argv[1]):
        sys.stdout.write(line + "\n")
PY
then
  log_warn "DOCX extraction failed: $bn"
  exit 1
fi

# Prepare CSV header if needed
if [[ -n "${csv:-}" && ! -s "$csv" ]]; then
  printf 'file,page,text,method,used_ocr\n' > "$csv"
fi

# Clean & gather text for CSV (no TXT artifacts on disk)
cleaned="$(sed 's/\r//g' "$tmp_txt" | sed ':a;N;$!ba;s/\n/\\n/g')"
cleaned="${cleaned//\"/\"\"}"  # CSV-escape quotes

# Sanity: require some non-whitespace
chars="$(tr -d '\n\r\t ' <<< "$(sed 's/\\n//g' <<< "$cleaned")" | wc -c | awk '{print $1}')"
if [[ "$chars" -lt 20 ]]; then
  log_warn "DOCX produced too little text ($chars chars): $bn"
  exit 1
fi

# Append single-row summary to CSV (per file)
if [[ -n "${csv:-}" ]]; then
  printf '"%s",%d,"%s","%s",%s\n' "$file" 1 "$cleaned" "docx" false >> "$csv"
fi

log_info "DOCX extraction complete (CSV-only): $bn"
exit 0
