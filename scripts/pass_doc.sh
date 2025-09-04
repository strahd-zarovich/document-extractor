#!/usr/bin/env bash
# pass_doc.sh — DOCX full-text extractor (no LibreOffice)
# Args: <file> <csv_out> <json_out> <out_dir>
set -Eeuo pipefail

file="$1"
csv="$2"   # kept for signature; not used here
json="$3"  # kept for signature; not used here
out_dir="$4"

# Load config & helpers if present
if [[ -n "${CONFIG_FILE:-}" && -f "${CONFIG_FILE}" ]]; then
  # shellcheck disable=SC1090
  . "${CONFIG_FILE}"
fi
# shellcheck disable=SC1091
. /app/scripts/common.sh

bn="$(basename -- "$file")"
ext="${bn##*.}"
ext_lc="$(printf '%s' "$ext" | tr 'A-Z' 'a-z')"

# Only DOCX supported here; .doc should be routed to Manual Review by caller
if [[ "$ext_lc" != "docx" ]]; then
  log_warn "pass_doc: unsupported extension without LibreOffice: $bn"
  exit 1
fi

out_txt="${out_dir}/${bn}.txt"
tmp_txt="$(mktemp -t docx_alltext.XXXXXX)"
trap 'rm -f "$tmp_txt"' EXIT

# Python: parse DOCX XML parts and extract text from paragraphs everywhere
if ! command -v python3 >/dev/null 2>&1; then
  log_error "python3 not available for DOCX extraction: $bn"
  exit 1
fi

if ! python3 - "$file" > "$tmp_txt" 2>/dev/null <<'PY'
import sys, zipfile, xml.etree.ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

def text_from_paragraphs(xml_bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return []
    lines = []
    # find all paragraphs anywhere in the part (tables, textboxes, etc. contain w:p)
    for p in root.findall('.//w:p', NS):
        runs = [t.text or "" for t in p.findall('.//w:t', NS)]
        line = "".join(runs).strip()
        if line:
            lines.append(line)
    return lines

def collect(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        want = []
        # document body
        if 'word/document.xml' in z.namelist():
            want.append(('BODY', 'word/document.xml'))
        # headers/footers (any number)
        for name in z.namelist():
            if name.startswith('word/header') and name.endswith('.xml'):
                want.append(('HEADER', name))
            elif name.startswith('word/footer') and name.endswith('.xml'):
                want.append(('FOOTER', name))
        # footnotes/endnotes/comments (if present)
        for part, label in [('word/footnotes.xml', 'FOOTNOTES'),
                            ('word/endnotes.xml',  'ENDNOTES'),
                            ('word/comments.xml',  'COMMENTS')]:
            if part in z.namelist():
                want.append((label, part))

        out_lines = []
        for label, name in want:
            try:
                xml_bytes = z.read(name)
            except KeyError:
                continue
            lines = text_from_paragraphs(xml_bytes)
            if lines:
                # Add a blank line between sections; omit labels to keep plain text simple
                if out_lines:
                    out_lines.append("")
                out_lines.extend(lines)
        return out_lines

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(2)
    path = sys.argv[1]
    lines = collect(path)
    sys.stdout.write("\n".join(lines))
PY
then
  log_warn "DOCX extraction failed: $bn"
  exit 1
fi

# Write cleaned text (strip CRs & trailing spaces)
mkdir -p "$out_dir"
> "$out_txt"
while IFS= read -r line; do
  cl="$(printf '%s' "$line" | tr -d '\r' | sed 's/[ \t]*$//')"
  [[ -z "$cl" ]] && { echo "" >> "$out_txt"; continue; }
  printf '%s\n' "$cl" >> "$out_txt"
done < "$tmp_txt"

# Sanity: require some non-whitespace
chars="$(tr -d '\n\r\t ' < "$out_txt" | wc -c | awk '{print $1}')"
if [[ "$chars" -lt 20 ]]; then
  log_warn "DOCX produced too little text ($chars chars): $bn"
  exit 1
fi

log_info "DOCX full-text extraction complete (no LibreOffice): $bn"
exit 0
