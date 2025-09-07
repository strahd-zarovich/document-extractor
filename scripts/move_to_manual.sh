#!/usr/bin/env bash
# move_to_manual.sh — move a file into the run's "Mandatory Review" folder and log why
# Args: <file> <reason>
set -Eeuo pipefail

file="$1"
reason="${2:-No reason provided}"

# Load logger if available
if [ -f /app/scripts/common.sh ]; then
  # shellcheck disable=SC1091
  . /app/scripts/common.sh
fi

# OUT_PATH should be exported by process_run.sh
dest_root="${OUT_PATH:-}"
if [ -z "$dest_root" ] || [ ! -d "$dest_root" ]; then
  # Fallback: file's directory (shouldn't happen in normal runs)
  dest_root="$(dirname -- "$file")"
fi

dest_dir="${dest_root}/Mandatory Review"
mkdir -p -- "$dest_dir"

bn="$(basename -- "$file")"
name="${bn%.*}"
ext="${bn##*.}"

dest="${dest_dir}/${bn}"
if [ -e "$dest" ]; then
  ts="$(date +%Y%m%d_%H%M%S)"
  # If there's no extension, avoid trailing dot
  if [ "$name" = "$bn" ]; then
    dest="${dest_dir}/${bn}_${ts}"
  else
    dest="${dest_dir}/${name}_${ts}.${ext}"
  fi
fi

mv -f -- "$file" "$dest"

if command -v log_info >/dev/null 2>&1; then
  log_info "Moved to Mandatory Review: $(basename -- "$dest") — reason: $reason"
else
  echo "[INFO] Moved to Mandatory Review: $(basename -- "$dest") — reason: $reason"
fi
