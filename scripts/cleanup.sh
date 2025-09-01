#!/bin/bash
set -euo pipefail

# Cleanup on container start – clears manifests and temp files

source /app/config.conf
source /app/scripts/common.sh

log_info "Running startup cleanup..."

# Delete manifest files
rm -f "$MANIFEST_DIR"/*.list 2>/dev/null || true

# Delete all tmp files
rm -rf "$TMP_DIR"/* 2>/dev/null || true

# Recreate directories to be safe
mkdir -p "$INPUT_DIR" "$OUTPUT_DIR" "$MANUAL_REVIEW_DIR" "$TMP_DIR" "$MANIFEST_DIR"

# Ensure permissions are correct
/app/scripts/fix_permissions.sh

log_info "Cleanup complete – manifests and tmp cleared."
