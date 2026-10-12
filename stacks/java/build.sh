#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
P="${1:-.}"
P="$(cd "$P" 2>/dev/null && pwd)" || { echo "ERROR: project path not found: $P" >&2; exit 2; }
source "$ROOT/core/validation_rules.sh"
if [[ -x "$P/gradlew" ]]; then cd "$P" && ./gradlew build; elif [[ -f "$P/pom.xml" ]] && command -v mvn >/dev/null 2>&1; then cd "$P" && mvn -B package; else skip_check "Java build" "Gradle/Maven missing"; fi
