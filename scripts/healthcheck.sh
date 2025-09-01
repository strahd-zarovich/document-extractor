#!/bin/bash
set -euo pipefail

OUT_DIR="${OUTPUT_DIR:-/data/output}"
mkdir -p "$OUT_DIR" || exit 1

TEST_FILE="${OUT_DIR}/.healthcheck"
echo "ok" > "$TEST_FILE" 2>/dev/null || exit 1
rm -f "$TEST_FILE" || true
exit 0
