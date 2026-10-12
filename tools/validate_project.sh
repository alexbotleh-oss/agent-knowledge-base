#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-.}"
source "$ROOT/core/validation_rules.sh"
status=0
if command -v python3 >/dev/null 2>&1; then
  python3 -m json.tool "$ROOT/core/stack_registry.json" >/dev/null || { log "FAIL: invalid stack_registry.json"; status=1; }
  if [[ -f "$ROOT/tools/validate_memory.py" ]]; then
    python3 "$ROOT/tools/validate_memory.py" || status=1
  fi
else skip_check "registry/memory validation" "python3 not installed" || status=1; fi
for f in core/guardrails.md core/universal_instructions.md core/agent_runtime_protocol.md core/memory_model.md core/session_handoff.md core/context_interpretation.md core/autonomy_policy.md core/visual_diagnostics.md core/validation_rules.sh core/validation_router.sh; do
 [[ -s "$ROOT/$f" ]] || { log "FAIL: required file missing/empty: $f"; status=1; }
done
if bash "$ROOT/core/validation_router.sh" "$PROJECT"; then :; else rc=$?; log "FAIL: validation router (exit $rc)"; status=1; fi
exit "$status"
