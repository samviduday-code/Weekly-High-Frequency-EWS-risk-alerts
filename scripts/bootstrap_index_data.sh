#!/usr/bin/env bash
# Clone or link samviduday-code/index-data into INDEX_DATA_DIR (default: .data/index-data).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INDEX_DATA_DIR="${INDEX_DATA_DIR:-$ROOT/.data/index-data}"
REPO_URL="${INDEX_DATA_REPO:-https://github.com/samviduday-code/index-data.git}"

discover_checked_out_index_data() {
  local candidate
  for candidate in \
    "${INDEX_DATA_DIR}" \
    "/agent/repos/index-data" \
    "/agent/repos/Index-data" \
    "/agent/repos/index_data" \
    "$ROOT/../index-data"; do
    if [[ -d "$candidate/New/external_hf" ]] || [[ -d "$candidate/.git" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

mkdir -p "$(dirname "$INDEX_DATA_DIR")"

if existing="$(discover_checked_out_index_data)"; then
  if [[ "$existing" != "$INDEX_DATA_DIR" ]]; then
    rm -rf "$INDEX_DATA_DIR"
    ln -sfn "$existing" "$INDEX_DATA_DIR"
    echo "index-data: linked $INDEX_DATA_DIR -> $existing"
  else
    echo "index-data: using $INDEX_DATA_DIR"
  fi
  echo "INDEX_DATA_DIR=$INDEX_DATA_DIR"
  exit 0
fi

if [[ -d "$INDEX_DATA_DIR/.git" ]]; then
  echo "index-data: pulling latest in $INDEX_DATA_DIR"
  git -C "$INDEX_DATA_DIR" pull --ff-only
else
  echo "index-data: cloning $REPO_URL -> $INDEX_DATA_DIR"
  if ! git clone --depth 1 "$REPO_URL" "$INDEX_DATA_DIR"; then
    echo "index-data: clone failed (check repo is on the Cloud Agent environment and GitHub grants access)" >&2
    if [[ "${BOOTSTRAP_OPTIONAL:-}" == "1" ]]; then
      echo "index-data: continuing (BOOTSTRAP_OPTIONAL=1)" >&2
      exit 0
    fi
    exit 1
  fi
fi

echo "INDEX_DATA_DIR=$INDEX_DATA_DIR"
