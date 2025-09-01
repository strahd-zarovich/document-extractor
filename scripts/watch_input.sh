#!/bin/bash
set -euo pipefail

# Watches /input for new files and triggers processing
# Interval defined by INPUT_CHECK_INTERVAL in config.conf

source /app/config.conf
source /app/scripts/common.sh

log_info "Starting watch loop: scanning $INPUT_DIR every ${INPUT_CHECK_INTERVAL}s"

while true; do
    # Find all files under INPUT_DIR (excluding tmp)
    find "$INPUT_DIR" -type f ! -path "$TMP_DIR/*" | while read -r file; do
        # Skip hidden/system files
        [[ "$(basename "$file")" =~ ^\. ]] && continue

        log_debug "Found input file: $file"
        /app/scripts/process_file.sh "$file" || {
            log_warn "Processing failed for $file, moved to manual review."
            mv "$file" "$MANUAL_REVIEW_DIR/" 2>/dev/null || true
        }
    done

    # After processing, clean up empty dirs but NOT /input
    find "$INPUT_DIR" -mindepth 1 -type d -empty -exec rmdir {} \; 2>/dev/null || true

    sleep "$INPUT_CHECK_INTERVAL"
done
