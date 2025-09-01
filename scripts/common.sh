#!/bin/bash
set -Eeuo pipefail

# Bring in runtime config if available
if [[ -n "${CONFIG_FILE:-}" && -f "${CONFIG_FILE}" ]]; then
  # shellcheck disable=SC1090
  . "${CONFIG_FILE}"
fi

# ---------- Logging ----------
log_debug() {
    if [[ "${LOG_LEVEL:-DEBUG}" == "DEBUG" ]]; then
        echo "[DEBUG] $1"
    fi
}
log_info() {
    echo "[INFO] $1"
}
log_warn() {
    echo "[WARN] $1"
}
log_error() {
    echo "[ERROR] $1" >&2
}

# ---------- File Processing ----------
process_file() {
    local file="$1"
    local run_name="$2"
    local csv="$3"
    local json="$4"
    local out_path="$5"

    local filename ext
    filename=$(basename "$file")
    ext="${filename##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

    log_info "Processing: $filename"

    case "$ext" in
        doc|docx)
            /app/scripts/pass_doc.sh "$file" "$csv" "$json" "$out_path" || move_to_manual "$file" "$out_path" "DOCX_FAIL" "Extraction failed"
            ;;
        pdf)
            /app/scripts/pass_pdf.sh "$file" "$csv" "$json" "$out_path" || move_to_manual "$file" "$out_path" "PDF_FAIL" "Extraction failed"
            ;;
        txt)
            /app/scripts/pass_txt.sh "$file" "$csv" "$json" "$out_path" || move_to_manual "$file" "$out_path" "TXT_FAIL" "Extraction failed"
            ;;
        *)
            log_warn "Unsupported extension: $ext"
            move_to_manual "$file" "$out_path" "UNSUPPORTED" "Extension $ext"
            return 0
            ;;
    esac

    # Delete successfully processed file
    if [[ -f "$file" ]]; then
        rm -f "$file"
        log_debug "Deleted source file after successful processing: $filename"
    fi
}

move_to_manual() {
    local file="$1"
    local out_path="$2"
    local reason="$3"
    local note="$4"

    mkdir -p "$out_path/Mandatory Review"
    mv -f "$file" "$out_path/Mandatory Review/" 2>/dev/null || cp -f "$file" "$out_path/Mandatory Review/" 2>/dev/null
    echo "$(basename "$file"),$reason,$note" >> "$out_path/review_manifest.csv"
    log_warn "Moved to Mandatory Review: $(basename "$file") [$reason]"
}
