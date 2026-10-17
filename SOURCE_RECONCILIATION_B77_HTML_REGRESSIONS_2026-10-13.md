# Bounded source reconciliation — B77 HTML recipe regressions

Date: 2026-10-13  
Project: B77_HTML_PWA (HTML/SQLite prototype), kept separate from N99 / RECIPE_MANAGER Android Flet.

## Claim under review

The extraction report summarizes user-reported regressions in successive HTML candidates: the recipe list stopped populating after database additions, importing recipes from the database failed, nutrition/KБЖУ display disappeared, and recipe deletion plus kcal/100 g / protein / fat / carbohydrate labels were lost.

## Canonical memory cross-check

- `EVT-B77-20260922-002` records the same group of reported symptoms, explicitly marks root cause unknown, and says candidate-to-candidate diff and final browser/runtime result are not established.
- `EVT-B77-20260922-001` records related ingredient-normalization false positives/negatives and the broken database-access path, while leaving implementation outcome unknown.
- `B77-L-012` converts the recurrence into a regression-prevention lesson: compare against a named working baseline and verify database read/import, recipe list, nutrition, CRUD and persistence separately.

## Result

**Status: consistent report-to-canonical-memory match for this bounded claim.** The memory preserves the symptoms and does not promote them into a verified root cause or a claimed fix. The separate B77 records also prevent incorrectly treating these HTML/SQLite symptoms as evidence of an N99 Android/Flet defect.

## Evidence limitations

The primary chat messages and original HTML/SQLite artifacts were not reopened in this pass; the event records cite specific source conversations, but independent primary-source corroboration remains pending. No final HTML candidate, database, or browser runtime was tested here.

## Next step

Continue with a separate claim from the extraction report. For eventual project-level validation, recover the exact known-working HTML baseline and candidate, compare their diffs, and test import/list/nutrition/delete/persistence. Do not claim the regression fixed until the delivered artifact passes those checks.
