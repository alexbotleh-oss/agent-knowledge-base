#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:?Usage: tools/install_into_repo.sh /path/to/target-repo}"
DEST="$(cd "$DEST" && pwd)"
[[ "$SRC" != "$DEST" ]] || { echo "Source and destination are the same directory" >&2; exit 2; }
git -C "$DEST" rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Destination is not a git repository" >&2; exit 2; }
command -v rsync >/dev/null 2>&1 || { echo "rsync is required" >&2; exit 2; }
rsync -av --ignore-existing --exclude='.git' "$SRC/" "$DEST/"
echo "Copied only missing files. Review with: git -C \"$DEST\" status --short"
