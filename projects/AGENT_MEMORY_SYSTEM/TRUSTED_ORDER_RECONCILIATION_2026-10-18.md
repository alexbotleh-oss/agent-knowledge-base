# Trusted-order reconciliation for AGENT_MEMORY_SYSTEM event journal

Status: **PARTIAL — read-only evidence review; ancestry verified for the explicitly commit-based 18 October chain, but no trusted-order file has been applied to the live journal.**

Reviewed against branch `export/cross-project-experience-rollup-20261012`, HEAD `da9af8316de43ed0b0480f87d7fe079846488be5`, on 2026-10-18. The event source is `projects/AGENT_MEMORY_SYSTEM/events.jsonl`. This note does not modify that source.

## Rules used

- `event_time` with day precision can establish ordering between different dates, but cannot order two events on the same date.
- `recorded_at`, JSONL row position, event ID numbering, and commit timestamp alone are not treated as proof of event chronology.
- A relation explicitly described as Git commit ancestry is validated using GitHub compare results (ancestor/descendant), not merely commit timestamps or list position.
- An append-only `edge_corrections` overlay changes the effective projection only. It does not rewrite the original event row.
- A missing or ambiguous order remains unresolved; no synthetic rank is assigned to force a PASS.

## Evidence review

| Effective temporal relation | Current evidence | Disposition |
|---|---|---|
| `EVT-AGMS-20261013-002 preceded_by EVT-AGMS-20261013-001` | Overlay in `EVT-AGMS-20261013-006` reverses the original edge direction. Both events have only `2026-10-13` day precision. | **UNRESOLVED** as event chronology. The overlay preserves the correction, but day-level dates alone do not prove intra-day order. |
| `EVT-AGMS-20261013-003 preceded_by EVT-AGMS-20261013-002` | Same-day records; direction was changed by the correction overlay in `EVT-AGMS-20261013-006`. | **UNRESOLVED** as event chronology. |
| `EVT-AGMS-20261013-004 preceded_by EVT-AGMS-20261013-003` | Same-day records; direction was changed by the correction overlay in `EVT-AGMS-20261013-006`. | **UNRESOLVED** as event chronology. |
| `EVT-AGMS-20261014-001 preceded_by EVT-AGMS-20261013-006` | Source dates differ: 2026-10-14 vs 2026-10-13. The correction in `EVT-AGMS-20261014-002` changes the original edge direction. | **DATE-ORDER SUPPORTED** (the 14 October event is later by date). |
| `EVT-AGMS-20261014-002 preceded_by EVT-AGMS-20261014-001` | Both events have day-level precision on 2026-10-14. The second event is a review/correction, but that alone is not a timestamp for the event chronology being asserted. | **UNRESOLVED** pending explicit source chronology or a clearly scoped commit-ancestry claim. |
| `EVT-AGMS-20261014-003 followed_by EVT-AGMS-20261014-002` | `EVT-AGMS-20261014-004` contains `corrected_relation: null` for this edge. | **REMOVED FROM EFFECTIVE PROJECTION**; do not validate or restore this edge. The original row remains immutable. |
| `EVT-AGMS-20261018-001 preceded_by EVT-AGMS-20261014-004` | Source dates differ: 18 October vs 14 October. | **DATE-ORDER SUPPORTED**. |
| Relations among `EVT-AGMS-20261018-001..008` | Their records explicitly cite Git commit ancestry. GitHub compare was run for each adjacent pair of event-append commits listed here: `9408440fe0fe40f084a09f93024062ac9f500b23`, `869fbd14d8478c0f2c25f62dd86e4c2e89bdf689`, `17defdb08e634d459ab3534b25f8199c9aa2d545`, `12527599707925f8d0618eca509b79e3d5a399d5`, `b1fdfbf4fdabefb3e54caf9678078ffea04904e1`, `5df320a5197a6c9e0fc481966689ce3b8313329b`, `446b952076081b3bdbcce38cf4acc8344a5cd109`, `bacdabe1b4e67b00c48aac9f3e208246346cff9b`. Every comparison returned `status=ahead`, `behind_by=0`, confirming the listed direction of commit ancestry. | **COMMIT ANCESTRY VERIFIED** for this adjacent chain. This validates the specifically claimed commit-order relations, not any unrelated same-day event-time ordering. |

## What this means for the preflight

A complete, evidence-backed `trusted_order` map is **not yet available**. The live journal preflight has therefore **not been run** with fabricated ranks, and the append writer has **not** been applied to the journal.

Next safe actions:

1. Use the verified 18 October commit-ancestry chain as evidence for those explicitly ancestry-based relations; do not generalize it to unrelated edges.
2. Obtain source-level timestamps or explicit ordering evidence for the unresolved 13 and 14 October relations; otherwise leave them unresolved and decide whether the model should support partial-order validation instead of forcing a total order.
3. Run `tools/validate_event_journal.py` read-only using only grounded evidence; preserve its complete report.
4. Do not append to the live journal unless every effective temporal edge is validated or explicitly removed by an existing correction overlay.

## Verification boundary

This is a **DOCUMENTED** evidence review, not an executed preflight. It does not establish that the full journal currently passes validation, and it does not certify attachment/archive completeness.
