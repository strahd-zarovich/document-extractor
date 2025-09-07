#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

# -------- Defaults (overridable via env) --------
: "${INPUT_DIR:=/data/input}"
: "${OUTPUT_DIR:=/data/output}"
: "${WORK_DIR:=/tmp/work}"
: "${LOG_DIR:=/data/logs}"
: "${RUNTIME_CFG_DIR:=/data/config}"

: "${INPUT_CHECK_INTERVAL:=15s}"   # used by 'sleep'; supports "15s"
: "${INPUT_STABLE_SECS:=15}"       # used by inotifywait -t; must be integer seconds

: "${LOG_LEVEL:=INFO}"
: "${PUID:=99}"
: "${PGID:=100}"
: "${UMASK:=0002}"
umask "$UMASK"

# Python runtime
export PYTHONUNBUFFERED=1
export PYTHONPATH=/app/scripts

# -------- Tiny logger --------
log() { printf '[%(%Y-%m-%d %H:%M:%S)T] [%s] %s\n' -1 "${1:-INFO}" "${*:2}"; }

# -------- Ensure /data tree exists & is writable --------
ensure_data_tree() {
  local created=0
  for d in "$INPUT_DIR" "$OUTPUT_DIR" "$LOG_DIR" "$RUNTIME_CFG_DIR" "$WORK_DIR"; do
    if [[ ! -d "$d" ]]; then mkdir -p "$d" && created=1; fi
  done
  chown -R "$PUID:$PGID" "$INPUT_DIR" "$OUTPUT_DIR" "$LOG_DIR" "$RUNTIME_CFG_DIR" "$WORK_DIR" 2>/dev/null || true
  chmod -R g+rwX         "$INPUT_DIR" "$OUTPUT_DIR" "$LOG_DIR" "$RUNTIME_CFG_DIR" "$WORK_DIR" 2>/dev/null || true
  if [[ $created -eq 1 ]]; then log INFO "Initialized data tree"; fi
  # writability probe (warn if bad)
  if ! sh -c "umask $UMASK; : > '$INPUT_DIR/.writable'"; then
    log ERROR "INPUT_DIR not writable: $INPUT_DIR (check volume mapping & PUID/PGID)"
  else
    rm -f "$INPUT_DIR/.writable"
  fi
}

# Prepare dirs before we tee logs
ensure_data_tree

# Mirror stdout/stderr to persistent file as well
exec > >(tee -a "$LOG_DIR/docker.log") 2>&1

# -------- Optional runtime config file --------
IMAGE_DEFAULT_CFG="/app/defaults/config.conf"
RUNTIME_CFG_FILE="${RUNTIME_CFG_DIR}/config.conf"
mkdir -p "${RUNTIME_CFG_DIR}"
if [[ ! -f "${RUNTIME_CFG_FILE}" && -f "${IMAGE_DEFAULT_CFG}" ]]; then
  cp -f "${IMAGE_DEFAULT_CFG}" "${RUNTIME_CFG_FILE}"
fi
[[ -f "${RUNTIME_CFG_FILE}" ]] && sed -i 's/\r$//' "${RUNTIME_CFG_FILE}" || true

log INFO "Startup settings: INPUT_DIR=$INPUT_DIR OUTPUT_DIR=$OUTPUT_DIR WORK_DIR=$WORK_DIR LOG_DIR=$LOG_DIR LOG_LEVEL=${LOG_LEVEL:-INFO} INPUT_CHECK_INTERVAL=$INPUT_CHECK_INTERVAL PUID=$PUID PGID=$PGID UMASK=$UMASK"

wait_for_quiescence() {
  local dir="$1"; local idle="${2:-15}"
  # If the dir is missing, create it and treat as quiescent
  [[ -d "$dir" ]] || { mkdir -p "$dir"; return 0; }
  while true; do
    # inotifywait exit codes: 0=event, 1=error, 2=timeout (i.e., idle for the whole -t)
    inotifywait -q -r -t "$idle" -e close_write,move,create,delete "$dir" >/dev/null 2>&1
    rc=$?
    if [[ $rc -eq 2 ]]; then
      log_info "Input idle for ${idle}s — proceeding."
      return 0
    fi
    # saw activity → loop and wait again
    log_debug "Input changed; waiting ${idle}s of quiet..."
  done
}

# -------- Helpers --------

# Safe run-name builder: ignores dotfiles; guarantees non-empty rn
build_run_name() {
  # $1 = top-level filename (basename only)
  local b="$1" stem
  [[ -z "$b" || "$b" = .* ]] && { echo ""; return; }                # dotfiles/empty -> invalid
  stem="${b%.*}"
  [[ -z "$stem" ]] && stem="run-$(date +%s)"
  # strip trailing dots/spaces
  stem="${stem%%*( )}"
  stem="${stem%%.}"
  [[ -z "$stem" ]] && stem="run-$(date +%s)"
  echo "$stem"
}

make_runs_from_top_files() {
  shopt -s nullglob
  for f in "$INPUT_DIR"/*; do
    [[ -f "$f" ]] || continue
    local base rn dest
    base="$(basename "$f")"
    rn="$(build_run_name "$base")"
    [[ -z "$rn" ]] && { log DEBUG "Skipping top-level file '$base' (ignored)"; continue; }
    dest="$INPUT_DIR/$rn"
    mkdir -p "$dest"
    mv -f -- "$f" "$dest/$base"
    log INFO "Top-level file detected. Created run '$rn' and moved '$base'."
  done
}

derive_run_names() {
  shopt -s nullglob
  # list only 1st-level subdirs (never the root)
  find "$INPUT_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort -u
}

process_run() {
  local rn="$1"
  local IN="$INPUT_DIR/$rn"
  local OUT="$OUTPUT_DIR/$rn"
  local TMP="$WORK_DIR/$rn"
  local RUNLOG="$OUT/run.log"

  # Guard against empty/invalid run name (never touch the input root)
  if [[ -z "${rn:-}" || "$IN" = "$INPUT_DIR" ]]; then
    log DEBUG "Skipping invalid run name silently"
    return 0
  fi

  mkdir -p "$OUT" "$TMP"
  chown -R "$PUID:$PGID" "$OUT" "$TMP" 2>/dev/null || true

  export RUN_NAME="$rn" RUN_PATH="$IN" OUT_PATH="$OUT" TMP_PATH="$TMP" RUN_LOG="$RUNLOG" LOG_LEVEL

  # single-run lock
  local LOCK="$TMP/.run.lock"
  if ! ( set -o noclobber; echo $$ > "$LOCK") 2>/dev/null; then
    log INFO "Run already in progress; skipping: $rn"
    return 0
  fi
  trap 'rm -f "$LOCK"' RETURN

  log INFO "Run start: $rn"

  # Run the Python orchestrator; ignore its RC (it does per-file quarantine itself)
  /app/scripts/process_run.sh 2>>"$LOG_DIR/python_errors.log" \
    || log WARN "process_run returned non-zero for $rn (ignored; file-level quarantine handled by processor)"

  # After processing, prune the run dir if it is now empty (never touch input root)
  if [[ -d "$IN" ]] && [[ -z "$(ls -A "$IN")" ]]; then
    rmdir "$IN" 2>/dev/null || true
  fi

  log INFO "Run end: $rn"

  chown -R "$PUID:$PGID" "$OUT" "$TMP" "$OUTPUT_DIR" "$LOG_DIR" 2>/dev/null || true
}

# -------- Main loop --------
while true; do
  # self-heal if the host/share dropped the folder
  [[ -d "$INPUT_DIR" ]] || mkdir -p "$INPUT_DIR"
  ensure_data_tree

  make_runs_from_top_files

  mapfile -t runs < <(derive_run_names || true)
  for rn in "${runs[@]}"; do
    # process only if the run dir contains at least one file
    if find "$INPUT_DIR/$rn" -mindepth 1 -type f -print -quit | grep -q .; then
      process_run "$rn"
    else
      # remove empty run dirs (never the input root)
      rmdir "$INPUT_DIR/$rn" 2>/dev/null || true
    fi
  done

  # prune *only* empty subdirs under input (guard root with mindepth)
  if [[ -d "$INPUT_DIR" ]]; then
    find "$INPUT_DIR" -mindepth 1 -maxdepth 1 -type d -empty -exec rmdir {} \; 2>/dev/null || true
  fi

  sleep "$INPUT_CHECK_INTERVAL"
done
