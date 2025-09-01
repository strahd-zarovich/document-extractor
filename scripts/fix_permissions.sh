#!/bin/bash
set -euo pipefail

# This script enforces UnRAID-friendly ownership/permissions
# Runs periodically or after new files are created

source /app/config.conf
source /app/scripts/common.sh

log_debug "Fixing file permissions in $INPUT_DIR and $OUTPUT_DIR"

# Ensure files are owned by nobody:users (99:100)
chown -R 99:100 "$INPUT_DIR" "$OUTPUT_DIR" "$TMP_DIR" 2>/dev/null || true

# Ensure readable/writable by owner and group
chmod -R ug+rw "$INPUT_DIR" "$OUTPUT_DIR" "$TMP_DIR" 2>/dev/null || true
