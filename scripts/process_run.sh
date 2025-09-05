#!/bin/bash
set -Eeuo pipefail

RUN_NAME="$1"
INPUT_DIR="${INPUT_DIR:-/data/input}"
OUTPUT_DIR="${OUTPUT_DIR:-/data/output}"

RUN_PATH="${INPUT_DIR}/${RUN_NAME}"
OUT_PATH="${OUTPUT_DIR}/${RUN_NAME}"
TMP_PATH="${WORK_DIR:-/tmp/work}/${RUN_NAME}"

mkdir -p "$OUT_PATH" "$TMP_PATH" "$OUT_PATH/Mandatory Review"

# Per-run log file (mirror of log_* output for this run)
RUN_LOG="${OUT_PATH}/run.log"
export RUN_LOG
{
  printf '--- Run start %s ---\n' "$(date +'%F %T')"
  printf 'RUN_NAME=%s\nINPUT=%s\nOUTPUT=%s\n' "$RUN_NAME" "$RUN_PATH" "$OUT_PATH"
} >> "$RUN_LOG" 2>/dev/null || true

# Ensure tmp is always cleaned (even on early exit)
trap 'rm -rf "$TMP_PATH"' EXIT

# Source runtime config & helpers
if [[ -n "${CONFIG_FILE:-}" && -f "${CONFIG_FILE}" ]]; then
  # shellcheck disable=SC1090
  . "${CONFIG_FILE}"
fi
# shellcheck disable=SC1091
. /app/scripts/common.sh

log_info "=== Processing run: $RUN_NAME ==="

# CSV/JSONL targets (named after RUN_NAME)
CSV_FILE="${OUT_PATH}/${RUN_NAME}.csv"
JSON_FILE="${OUT_PATH}/${RUN_NAME}.jsonl"

# -------- Replace-on-rerun handling --------
# Truthy if REPLACE_ON_RERUN is 1|true|yes (case-insensitive)
_replace="${REPLACE_ON_RERUN:-false}"
_replace="$(printf '%s' "$_replace" | tr '[:upper:]' '[:lower:]')"
if [[ "$_replace" == "1" || "$_replace" == "true" || "$_replace" == "yes" ]]; then
  log_info "REPLACE_ON_RERUN is enabled — truncating outputs for fresh run."
  # Truncate CSV with header, truncate JSONL, remove any per-PDF page index CSVs
  echo "filename,page,text" > "$CSV_FILE"
  : > "$JSON_FILE"
  find "$OUT_PATH" -maxdepth 1 -type f -name '*.pages.csv' -print -delete 2>/dev/null | while read -r del; do
    [[ -n "$del" ]] && log_debug "Deleted old page index: $del"
  done
else
  # Initialize outputs if new
  [[ -f "$CSV_FILE" ]] || echo "filename,page,text" > "$CSV_FILE"
  [[ -f "$JSON_FILE" ]] || : > "$JSON_FILE"
fi

# Export flag used by some legacy writers (safe)
export FIRST_JSON=true

# Iterate input files
find "$RUN_PATH" -type f | while read -r file; do
  # Auto-delete unsupported audio
  case "${file##*.}" in
    wav|WAV)
      log_info "Deleting unsupported audio (.wav): $(basename "$file")"
      rm -f -- "$file"
      continue
      ;;
  esac

  process_file "$file" "$RUN_NAME" "$CSV_FILE" "$JSON_FILE" "$OUT_PATH"
done

# Mark end of run in the per-run log
if [ -n "${RUN_LOG:-}" ]; then
  printf '--- Run complete %s ---\n' "$(date +'%F %T')" >> "$RUN_LOG" 2>/dev/null || true
fi

# Cleanup tmp for this run
rm -rf "$TMP_PATH"

# Prune empty subfolders under /input/<RUN_NAME>
find "$RUN_PATH" -mindepth 1 -type d -empty -print -delete | while read -r pruned; do
  [[ -n "$pruned" ]] && log_debug "Pruned empty folder: $pruned"
done

# Remove the now-empty top-level run folder itself (but NEVER /input)
if ! find "$RUN_PATH" -mindepth 1 -print -quit | grep -q . ; then
  if rmdir "$RUN_PATH" 2>/dev/null; then
    log_info "Removed empty run folder: $RUN_PATH"
  else
    log_warn "Could not remove empty run folder (permissions or in-use): $RUN_PATH"
  fi
fi

log_info "=== Completed run: $RUN_NAME ==="
