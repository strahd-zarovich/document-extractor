#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

# -------- Runtime-config handling (editable at runtime) ----------
RUNTIME_CFG_DIR="/data/config"
RUNTIME_CFG_FILE="${RUNTIME_CFG_DIR}/config.conf"
IMAGE_DEFAULT_CFG="/app/defaults/config.conf"

mkdir -p "${RUNTIME_CFG_DIR}"
if [[ ! -f "${RUNTIME_CFG_FILE}" ]]; then
  cp -f "${IMAGE_DEFAULT_CFG}" "${RUNTIME_CFG_FILE}"
fi

# Normalize line endings
sed -i 's/\r$//' "${RUNTIME_CFG_FILE}" || true
find /app -type f \( -name "*.sh" -o -name "*.conf" \) -exec sed -i 's/\r$//' {} + 2>/dev/null || true

# Make the config path available to all child scripts
export CONFIG_FILE="${RUNTIME_CFG_FILE}"

# Load runtime config (env may still override below)
# shellcheck disable=SC1090
. "${CONFIG_FILE}"

# -------- Defaults (env may override; config already loaded) ---------------
: "${INPUT_DIR:=/data/input}"
: "${OUTPUT_DIR:=/data/output}"
: "${LOG_DIR:=/data/logs}"
: "${WORK_DIR:=/tmp/work}"
: "${INPUT_CHECK_INTERVAL:=15}"
: "${LOG_LEVEL:=DEBUG}"
: "${PUID:=99}"
: "${PGID:=100}"
: "${UMASK:=002}"
: "${BIGPDF_SIZE_LIMIT_MB:=100}"
: "${BIGPDF_PAGE_LIMIT:=500}"

umask "${UMASK}"

# --- Create required folder hierarchy automatically ---
mkdir -p "${INPUT_DIR}" "${OUTPUT_DIR}" "${LOG_DIR}" "${WORK_DIR}"

# Apply UnRAID-friendly ownership & perms (do NOT touch host perms outside mount)
chown -R "${PUID}:${PGID}" "${OUTPUT_DIR}" "${LOG_DIR}" "${WORK_DIR}" "${INPUT_DIR}" 2>/dev/null || true
chmod 0775 "${OUTPUT_DIR}" "${LOG_DIR}" "${WORK_DIR}" "${INPUT_DIR}" 2>/dev/null || true
chmod g+s "${OUTPUT_DIR}" "${LOG_DIR}" "${INPUT_DIR}" 2>/dev/null || true

# Ensure runtime config is UnRAID-friendly (editable via SMB)
chown -R "${PUID}:${PGID}" "${RUNTIME_CFG_DIR}" 2>/dev/null || true
chmod 0775 "${RUNTIME_CFG_DIR}" 2>/dev/null || true
chmod 0664 "${RUNTIME_CFG_FILE}" 2>/dev/null || true
chmod g+s "${RUNTIME_CFG_DIR}" 2>/dev/null || true

log() {  # log <LEVEL> <msg>
  local level="$1"; shift || true
  if [[ "${LOG_LEVEL}" == "DEBUG" || "${level}" != "DEBUG" ]]; then
    printf '[%s] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$*" | tee -a "${LOG_DIR}/document-extractor.log"
  fi
}

log DEBUG "Startup settings: INPUT_DIR=${INPUT_DIR} OUTPUT_DIR=${OUTPUT_DIR} WORK_DIR=${WORK_DIR} LOG_DIR=${LOG_DIR} LOG_LEVEL=${LOG_LEVEL} INPUT_CHECK_INTERVAL=${INPUT_CHECK_INTERVAL}s BIGPDF_SIZE_LIMIT_MB=${BIGPDF_SIZE_LIMIT_MB} BIGPDF_PAGE_LIMIT=${BIGPDF_PAGE_LIMIT}"

# Clean tmp work and stale manifests (your requirement)
rm -rf "${WORK_DIR:?}/"* 2>/dev/null || true
find "${OUTPUT_DIR}" -maxdepth 2 -type f -name "manifest*.csv" -delete 2>/dev/null || true

# helper: derive run names from top-level dirs in INPUT_DIR
derive_run_names() { find "${INPUT_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort; }

# helper: quiescence (no size/count change across one interval) unless .ready present
quiescent_ready() {
  local dir="$1"
  [[ -f "${dir}/.ready" ]] && return 0
  local c1 s1 c2 s2
  c1=$(find "$dir" -type f | wc -l | tr -d ' ')
  s1=$(du -sb "$dir" | awk '{print $1}')
  sleep "${INPUT_CHECK_INTERVAL}"
  c2=$(find "$dir" -type f | wc -l | tr -d ' ')
  s2=$(du -sb "$dir" | awk '{print $1}')
  [[ "$c1" == "$c2" && "$s1" == "$s2" ]]
}

# guardrail for pruning
PRUNE_GUARD_ROOT="${INPUT_DIR}"

normalize_perms() {
  chown -R "${PUID}:${PGID}" "$@" 2>/dev/null || true
  find "$@" -type d -exec chmod 0775 {} + 2>/dev/null || true
  find "$@" -type f -exec chmod 0664 {} + 2>/dev/null || true
}

delete_source_and_prune() {  # delete_source_and_prune <file> <run>
  local src="$1" rn="$2"
  rm -f -- "$src" 2>/dev/null || true
  local d; d="$(dirname -- "$src")"
  # prune upward but never remove INPUT_DIR or INPUT_DIR/RUN_NAME
  while [[ "$d" != "/" && "$d" != "${PRUNE_GUARD_ROOT}" && "$d" != "${PRUNE_GUARD_ROOT}/${rn}" ]]; do
    rmdir --ignore-fail-on-non-empty "$d" 2>/dev/null || true
    d="$(dirname -- "$d")"
  done
  if [[ "$d" == "${PRUNE_GUARD_ROOT}" || "$d" == "${PRUNE_GUARD_ROOT}/${rn}" ]]; then
    log WARN "PRUNE_GUARD: attempted boundary at ${d}; skipped."
  fi
}

process_run() {
  local rn="$1"
  local in_top="${INPUT_DIR}/${rn}"
  local out_top="${OUTPUT_DIR}/${rn}"
  local work_top="${WORK_DIR}/${rn}"

  mkdir -p "${out_top}" "${work_top}" "${out_top}/Mandatory Review"
  normalize_perms "${out_top}" "${work_top}"

  log INFO "Processing RUN_NAME=${rn}"

  # Wait for folder to be stable unless .ready exists
  quiescent_ready "${in_top}" || return 0

  export RUN_NAME="${rn}" INPUT_DIR OUTPUT_DIR WORK_DIR LOG_DIR LOG_LEVEL BIGPDF_SIZE_LIMIT_MB BIGPDF_PAGE_LIMIT CONFIG_FILE

  # Only call the per-run orchestrator (it will iterate files & call pass scripts with args)
  /app/scripts/process_run.sh "${rn}"

  normalize_perms "${out_top}"
  log INFO "Completed RUN_NAME=${rn}"
}

# main loop: check for runs, process sequentially, no spammy poll logs
while true; do
  mapfile -t runs < <(derive_run_names || true)
  for rn in "${runs[@]}"; do
    process_run "$rn" || log ERROR "Run failed for ${rn}"
  done
  sleep "${INPUT_CHECK_INTERVAL}"
done
