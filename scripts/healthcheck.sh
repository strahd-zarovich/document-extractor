#!/bin/bash
set -euo pipefail

# Simple healthcheck: verify container is running and can write to /output
TEST_FILE="/output/.healthcheck"

echo "ok" > "$TEST_FILE" 2>/dev/null || exit 1
rm -f "$TEST_FILE" || true

exit 0
