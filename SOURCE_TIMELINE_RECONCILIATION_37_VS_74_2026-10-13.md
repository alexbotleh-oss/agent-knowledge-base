# Source timeline reconciliation: 37 vs 74 conversation counts — 2026-10-13

## Correction to the earlier interpretation

The discrepancy between 37 conversation objects in the inspected archive and a separate memory/report reference to 74 conversations must **not** be treated as evidence of an incorrect count, missing data, or an extraction defect by itself.

The user clarified the source timeline:
- The archive was submitted for archiving on 2026-10-05.
- It was returned on 2026-10-07.
- Development and information accumulation continued after the archive was produced.
- The merged memory can contain material gathered separately from individual chats and can therefore represent a later or differently scoped snapshot than the archive.

Thus the two counts may refer to different temporal cutoffs and/or different collection scopes. The archive count is a count of objects in that particular inspected archive; the count of 74 remains a separate historical claim whose exact snapshot and counting scope have not yet been established. Neither count should be silently substituted for the other.

## Required handling going forward

1. Treat every archive, merged-memory export, report, and chat extraction as a source snapshot with its own capture/creation/receipt time when known.
2. Distinguish event time, conversation time, export/archival time, receipt time, and the time a claim was added to merged memory. Do not collapse these into a single date.
3. Before comparing totals, establish the scope and cutoff of each dataset, whether counts mean chats, conversation objects, message IDs, or merged records, and whether later development was included.
4. If snapshot metadata is missing, mark the comparison as temporally/scopally unresolved rather than inferring an error from the numeric difference.
5. Preserve provenance and the user's explanation as a hypothesis grounded in the known workflow; do not claim exact reconciliation until the original scope/counting evidence is available.

## Current status

- Archive submitted: 2026-10-05 (user-provided).
- Archive returned: 2026-10-07 (user-provided).
- Development continued after return: yes (user-provided).
- Inspected archive count: 37 conversation objects and 10,034 distinct message IDs in the examined ZIP, as documented in PR #22.
- Other count: 74 conversations appears in a historical note; its exact source snapshot and counting method are not yet independently established.
- Conclusion: the timeline explanation is plausible and materially changes interpretation. The numeric discrepancy is **not evidence of a defect by itself**. Exact count reconciliation remains open pending snapshot/scope metadata.

## Scope guard

This is a memory/provenance correction only. Do not modify application code, databases, or APKs. Keep N99 / RECIPE_MANAGER, B77_HTML_PWA, CARD111, and ORGANISM separate.
