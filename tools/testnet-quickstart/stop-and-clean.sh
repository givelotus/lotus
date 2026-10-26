#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BIN_DIR="${LOTUS_BIN_DIR:-}"
if [[ -z "${BIN_DIR}" ]]; then
  for cand in \
    "${REPO_ROOT}/build/src" \
    "/private/tmp/out-wt-integrated-040/src" \
    "/private/tmp/build-lotus-v2-stress/src" \
    "/private/tmp/build-lotus-v2-unified/src"; do
    if [[ -x "${cand}/lotus-cli" ]]; then
      BIN_DIR="${cand}"
      break
    fi
  done
fi
LOTUS_CLI="${BIN_DIR}/lotus-cli"

POINTER_FILE="/private/tmp/lotus-v2-e2e-run-current"
TARGET_DIR="${1:-}"
if [[ -z "${TARGET_DIR}" && -f "${POINTER_FILE}" ]]; then
  TARGET_DIR="$(cat "${POINTER_FILE}" 2>/dev/null || true)"
fi

clean_run_dir() {
  local run_dir="$1"
  if [[ -z "${run_dir}" || ! -d "${run_dir}" ]]; then
    return 0
  fi
  echo "[stop-and-clean] Stopping services in ${run_dir}..."

  # Stop workbench & explorer servers
  for pidfile in "${run_dir}/workbench.pid" "${run_dir}/explorer.pid"; do
    if [[ -f "${pidfile}" ]]; then
      local pid
      pid="$(cat "${pidfile}" 2>/dev/null || true)"
      if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
        kill "${pid}" 2>/dev/null || true
        sleep 0.2
        kill -9 "${pid}" 2>/dev/null || true
      fi
    fi
  done

  # Stop lotusd nodes cleanly
  for i in 0 1 2; do
    local ndir="${run_dir}/node${i}"
    if [[ -d "${ndir}" ]]; then
      local rpcport=$((32110 + i * 10))
      if [[ -x "${LOTUS_CLI}" ]]; then
        "${LOTUS_CLI}" -regtest -datadir="${ndir}" -rpcport="${rpcport}" -rpcuser=lotusv2 -rpcpassword=lotusv2pass stop >/dev/null 2>&1 || true
      fi
    fi
  done

  # Wait for lotusd processes to exit completely before removing datadir
  for i in 0 1 2; do
    for pidfile in "${run_dir}/node${i}/lotusd.pid" "${run_dir}/node${i}/regtest/lotusd.pid" "${run_dir}/node${i}/regtest/bitcoind.pid"; do
      if [[ -f "${pidfile}" ]]; then
        local pid
        pid="$(cat "${pidfile}" 2>/dev/null || true)"
        if [[ -n "${pid}" ]]; then
          for _ in {1..50}; do
            if ! kill -0 "${pid}" 2>/dev/null; then
              break
            fi
            sleep 0.1
          done
          kill -9 "${pid}" 2>/dev/null || true
        fi
      fi
    done
  done

  echo "[stop-and-clean] Removing temporary datadir ${run_dir}..."
  rm -rf "${run_dir}"
}

if [[ -n "${TARGET_DIR}" ]]; then
  clean_run_dir "${TARGET_DIR}"
fi

# Also clean any stray /private/tmp/lotus-v2-e2e-run-* directories
for dir in /private/tmp/lotus-v2-e2e-run-*; do
  if [[ -d "${dir}" ]]; then
    clean_run_dir "${dir}"
  fi
done

rm -f "${POINTER_FILE}"
echo "[stop-and-clean] All Lotus V2 quickstart processes stopped and temporary directories removed."
