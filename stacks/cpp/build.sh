#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
P="${1:-.}"
P="$(cd "$P" 2>/dev/null && pwd)" || { echo "ERROR: project path not found: $P" >&2; exit 2; }
source "$ROOT/core/validation_rules.sh"
if [[ -f "$P/CMakeLists.txt" ]] && command -v cmake >/dev/null 2>&1; then cmake -S "$P" -B "$P/build" && cmake --build "$P/build"; elif [[ -f "$P/Makefile" ]] && command -v make >/dev/null 2>&1; then cd "$P" && make; else skip_check "C++ build" "CMake/Make missing"; fi
