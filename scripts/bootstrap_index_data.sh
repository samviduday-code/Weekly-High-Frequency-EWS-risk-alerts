#!/usr/bin/env bash
# Clone or refresh samviduday-code/index-data into INDEX_DATA_DIR (default: .data/index-data).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INDEX_DATA_DIR="${INDEX_DATA_DIR:-$ROOT/.data/index-data}"
REPO_URL="${INDEX_DATA_REPO:-https://github.com/samviduday-code/index-data.git}"

mkdir -p "$(dirname "$INDEX_DATA_DIR")"

if [[ -d "$INDEX_DATA_DIR/.git" ]]; then
  echo "index-data: pulling latest in $INDEX_DATA_DIR"
  git -C "$INDEX_DATA_DIR" pull --ff-only
else
  echo "index-data: cloning $REPO_URL -> $INDEX_DATA_DIR"
  git clone --depth 1 "$REPO_URL" "$INDEX_DATA_DIR"
fi

echo "INDEX_DATA_DIR=$INDEX_DATA_DIR"
