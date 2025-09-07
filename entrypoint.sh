#!/usr/bin/env bash
set -Eeuo pipefail

# ---------- Logging (must be defined before first use) ----------
log() {
  local level="${1:-INFO}"; shift || true
  local ts
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "[$ts] [$level] $*"
  if [[ -n "${LOG_DIR:-}" ]]; then
    mkdir -p "$LOG_DIR" 2>/dev/null || true
    printf "[%s] [%s] %s\n" "$ts" "$level" "$*" >> "$LOG_DIR/docker.log" 2>/dev/null || true
  fi
}

# ---------- Resolve this script's absolute path (no hard-coded /app/...) ----------
SCRIPT_SELF="${BASH_SOURCE[0]:-$0}"
if [[ "${SCRIPT_SELF:0:1}" != "/" ]]; then
  SCRIPT_SELF="$(pwd)/$SCRIPT_SELF"
fi
SCRIPT_DIR="$(cd -P -- "$(dirname -- "$SCRIPT_SELF")" && pwd)"
SCRIPT_SELF="$SCRIPT_DIR/$(basename -- "$SCRIPT_SELF")"

# ---------- Config (defaults) ----------
INPUT_DIR="${INPUT_DIR:-/data/input}"
OUTPUT_DIR="${OUTPUT_DIR:-/data/output}"
WORK_DIR="${WORK_DIR:-/data/tmp}"
LOG_DIR="${LOG_DIR:-/data/logs}"

INPUT_STABLE_SECS="${INPUT_STABLE_SECS:-15}"
INPUT_CHECK_INTERVAL="${INPUT_CHECK_INTERVAL:-15}"

PUID="${PUID:-99}"
PGID="${PGID:-100}"
UMASK="${UMASK:-0002}"

PASS_TXT_CUTOFF="${PASS_TXT_CUTOFF:-0.75}"
PASS_DOC_CUTOFF="${PASS_DOC_CUTOFF:-0.75}"
PASS_OCR_A_CUTOFF="${PASS_OCR_A_CUTOFF:-0.65}"
PASS_OCR_B_CUTOFF="${PASS_OCR_B_CUTOFF:-0.55}"
BIGPDF_SIZE_LIMIT_MB="${BIGPDF_SIZE_LIMIT_MB:-50}"
BIGPDF_PAGE_LIMIT="${BIGPDF_PAGE_LIMIT:-500}"

# ---------- Prepare directories & perms ----------
mkdir -p "$INPUT_DIR" "$OUTPUT_DIR" "$WORK_DIR" "$LOG_DIR"
umask "$UMASK"
chown -R "${PUID}:${PGID}" "$INPUT_DIR" "$OUTPUT_DIR" "$WORK_DIR" "$LOG_DIR" || true

# Ensure the running script and its directory are traversable by unprivileged user
chmod a+rx "$SCRIPT_DIR" "$SCRIPT_SELF" || true
# Best-effort: if these exist, make them traversable too (harmless if absent)
[[ -d /app ]] && chmod a+rx /app || true
[[ -d /app/scripts ]] && chmod a+rx /app/scripts || true

# ---------- Drop privileges once (if running as root and gosu available) ----------
if [[ -z "${RUN_AS_HELPER:-}" && "$(id -u)" == "0" ]]; then
  if command -v gosu >/dev/null 2>&1; then
    export RUN_AS_HELPER=1
    exec gosu "${PUID}:${PGID}" /usr/bin/env bash "$SCRIPT_SELF"
  else
    log WARNING "gosu not found; continuing as root. Prefer setting container user to 99:100 or install gosu."
  fi
fi

# ---------- Startup echo ----------
log INFO "Startup config:"
log INFO "  INPUT_DIR=$INPUT_DIR"
log INFO "  OUTPUT_DIR=$OUTPUT_DIR"
log INFO "  WORK_DIR=$WORK_DIR"
log INFO "  LOG_DIR=$LOG_DIR"
log INFO "  PUID=$PUID PGID=$PGID UMASK=$UMASK"
log INFO "  STABLE_SECS=$INPUT_STABLE_SECS CHECK_INTERVAL=$INPUT_CHECK_INTERVAL"
log INFO "  CUT_OFFS: TXT=$PASS_TXT_CUTOFF DOC=$PASS_DOC_CUTOFF OCR_A=$PASS_OCR_A_CUTOFF OCR_B=$PASS_OCR_B_CUTOFF"
log INFO "  BIGPDF thresholds: SIZE_MB=$BIGPDF_SIZE_LIMIT_MB PAGES=$BIGPDF_PAGE_LIMIT"

python3 - <<'PY' 2>/dev/null || true
import importlib
def v(m):
    try:
        mod = importlib.import_module(m)
        return getattr(mod, '__version__', 'unknown')
    except Exception:
        return 'missing'
print(f"[VERSIONS] PyMuPDF={v('fitz')} pdfminer={v('pdfminer')} Pillow={v('PIL')} pytesseract={v('pytesseract')}")
PY

# ---------- Main watcher loop ----------
log INFO "Watcher starting as $(id -u):$(id -g); waiting for input quiescence..."
while true; do
  # Quiescence wait
  if command -v inotifywait >/dev/null 2>&1; then
    if inotifywait -q -t "$INPUT_STABLE_SECS" -r -e modify,move,create,delete "$INPUT_DIR"; then
      sleep 1
      continue
    fi
  else
    sleep "$INPUT_STABLE_SECS"
  fi

  shopt -s nullglob
  entries=("$INPUT_DIR"/*)
  shopt -u nullglob

  if [[ ${#entries[@]} -eq 0 ]]; then
    sleep "$INPUT_CHECK_INTERVAL"
    continue
  fi

  for item in "${entries[@]}"; do
    base="$(basename "$item")"
    [[ "$base" == "." || "$base" == ".." ]] && continue

    if [[ -f "$item" ]]; then
      run_name="${base%.*}"
      run_dir="$INPUT_DIR/$run_name"
      mkdir -p "$run_dir"
      mv -f "$item" "$run_dir/"
      log INFO "Created run from file: $base -> $run_name"
    elif [[ -d "$item" ]]; then
      run_dir="$item"
      run_name="$base"
      log INFO "Found run directory: $run_name"
    else
      continue
    fi

    run_out_dir="$OUTPUT_DIR/$run_name"
    run_log="$run_out_dir/run.log"
    mkdir -p "$run_out_dir"

    export INPUT_DIR OUTPUT_DIR WORK_DIR LOG_DIR \
           PASS_TXT_CUTOFF PASS_DOC_CUTOFF PASS_OCR_A_CUTOFF PASS_OCR_B_CUTOFF \
           BIGPDF_SIZE_LIMIT_MB BIGPDF_PAGE_LIMIT

    log INFO "Process run: $run_name"
    python3 /app/scripts/process_run.py "$run_dir" "$run_out_dir" "$run_log" || true
  done

  sleep "$INPUT_CHECK_INTERVAL"
done
