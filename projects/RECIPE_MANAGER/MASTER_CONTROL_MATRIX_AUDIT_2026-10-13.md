# Audit of the Recipe Manager master control matrices — 2026-10-13

## Purpose and evidence boundary

This file preserves a concise, source-grounded index of the control-matrix workbooks found in the ChatGPT Library during the memory-transfer audit. It is a **summary of project artifacts**, not a fresh test report and not a claim that the application implements the listed functions.

### Source artifacts inspected

All five files were found in the Library under `/Б77/`; the folder location alone does **not** prove every row belongs exclusively to B77.

- `RecipeManager_MASTER_CONTROL_MATRIX_v1_2_20261002.xlsx` — modified 2026-10-02 19:58 UTC; extracted sheet text shows 9 tabs: control matrix, KTP, open decisions, platform status, prohibitions, new decisions, timers, Lite Cook, canonical workflow.
- `RecipeManager_MASTER_CONTROL_MATRIX_v1_1_20261002.xlsx` — modified 2026-10-02 18:48 UTC; 7 tabs.
- `RecipeManager_MASTER_CONTROL_MATRIX_v1_20261002.xlsx` — modified 2026-10-02 13:54 UTC.
- `RecipeManager_V20_FIX6_HTML_контрольная_матрица_20261002.xlsx` — modified 2026-10-02 20:22 UTC; single-sheet comparison of V20/FIX6/HTML.
- `RecipeManager_сводка_изменений_FIX6_V20_V21_N99.xlsx` — modified 2026-10-02 13:30 UTC; 5 tabs including summary, actually removed features, N99 regressions, rules and legend.

The spreadsheet text was read through Library extraction. Raw XLSX bytes were not available for independent binary-level inspection in this session. Preserve these filenames and timestamps as source provenance; do not imply the files were added to GitHub.

## Source hierarchy recorded by the matrices

- **V20** (`Что_приготовить_v20_category_checkbox.html`) is the visual/layout and interaction reference; do not invent a new layout when the task is to restore missing functionality.
- **FIX6** is a source of existing Flet behavior, not proof of feature completeness.
- The **HTML prototype** is a test surface for exercising full workflows and dependencies before porting validated behavior to Flet; v23 is labelled a candidate requiring acceptance, not a proven finished build.
- The working Flet scanner target is **native Android scanner only**. Legacy WebView/CDN/html5-qrcode and old-scanner fallback are listed as prohibited paths.
- One domain/Core contract should own normalization, availability, aggregation and business rules; HTML/PWA and Flet are presentation/runtime surfaces, not independent implementations of those rules.
- The workbook is mixed-scope. Raw messages establish that the HTML-first prototype phase was part of N99/RECIPE_MANAGER; the separate B77 iPhone-oriented HTML/WMA/PWA camera chain must remain separate. Attribute each source event by message-level evidence, not by the word “HTML” or the Library folder name.

## Functional invariants and acceptance focus

### Products and batches

- Use canonical `product_id`, canonical name/aliases, barcode, category, food/household and product/non-product classification.
- A product may have multiple batches; quantity, unit and expiry belong to the batch, and availability aggregates across batches.
- Editing an already-saved expiry date is an explicit user-reported gap (`EVT-RM-20261002-001`); the workbook marks batch/expiry behavior PARTIAL. Do not claim the edit path is fixed.
- Keep brand, package/variant, nutrition, category and other product fields when editing. Avoid duplicates after scanning or purchase transfer.

### Recipes, ingredients and availability

- Preserve raw ingredient text separately from normalized/canonical identity, product link, quantity, unit, qualifier/equivalent and confidence.
- Preserve ordered cooking steps; keep tips separate from steps; retain time, temperature, servings, difficulty, favorites and nutrition.
- Recipe nutrition requires calories, protein, fat and carbohydrates, with per-100-g display. Historical nutrition/deletion regressions remain evidence of risk, not proof of a current defect in every platform.
- Availability states are `OK / PARTIAL / MISSING / UNKNOWN`; do not infer compatibility for ambiguous units.
- Diet status and product availability are separate. Diet results should expose status plus reason rather than silently removing recipes.

### Cooking, Lite Cook and Shopping

- Missing ingredients become `ShoppingNeed` records linked to `recipe_id`, `product_id`, required/available/deficit and source recipe IDs.
- Aggregate shopping by `(product_id, unit_id)`, not by display name. Preserve purchase state, undo, source and purchased-to-product transfer; a purchased item becomes a product batch without creating a false duplicate.
- The v1.2 matrix records Lite Cook as a planned workflow: choose 1 or 2 dishes, choose starting dish when two are selected, check availability before cooking, offer shopping before steps, allow manual shopping items, return from shopping to products/recipe, and allow “cook now” when the user declines shopping.
- Two-dish cooking is one `CookingSession` with two dish slots and independent current steps; swipe vertically between dishes. A timer appears only when the current step has time; maximum two concurrent timers, one per dish. Timer persistence/notifications are marked NOT_READY in the matrix snapshot.

### Scanner

- Flet: native Android scanner only; preserve separate Products, Shopping and QR contexts with a shared result handler.
- Local-first lookup; known codes should map to existing products and not create duplicates.
- Unknown/unlinked codes require an explicit user choice (link, create or defer); do not silently create an incomplete product.
- Shopping scan should match a shopping item and mark it bought, not automatically create a product. QR history/local mapping/sync is a distinct context.
- The v1.2 workbook describes PWA camera as a possible separate web capability, not a replacement for the native Flet scanner. Its status as a working feature is not verified by this workbook.

### Import, backup, family and diagnostics

- Import path: `RAW → parser → staging → preview → correction → validation → normalization → transaction → DB`. Never write WEB/PDF data directly to the live database.
- A listed website is not a working adapter. The workbook marks the real PDF adapter NOT_READY and WEB adapters NOT_READY/PARTIAL; PC DB schema/contract is an open question.
- Family exchange requires versions and explicit conflict resolution; no silent merge/replace. Keep settings backup separate from recipes/products/shopping data, with schema version, preview and rollback.
- Diagnostics should retain errors and support export/share. A static check or successful CI does not establish device/runtime acceptance.

## Open questions in the v1.2 snapshot

- Confirm scope and trusted rule source for Pevzner diet tables №1–15.
- Finalize Roulette candidate pool, active filters, availability threshold and repeated-result behavior.
- Decide which of the seven listed web recipe sources need working adapters in the first release.
- Define the accepted `recipes.db`/PC DB schema and import contract.
- Decide whether server-side family sync is needed beyond local file/JSON exchange.
- Treat PWA camera as a separate web capability; do not merge it into the native Flet scanner requirement.

The workbook explicitly states that KTP-21…KTP-28 must not be invented from a single row without their original source. The extracted v1.2 KTP sheet lists KTP-01…KTP-20 only.

## Status interpretation and later priority

The workbook uses labels such as READY, PARTIAL, NOT_READY, ACCEPTANCE and DECISION as a snapshot dated 2026-10-02. These are **matrix statuses**, not independently reproduced test results from this audit. Any claimed PASS must be backed by a specific artifact, version, scenario and observed result.

The later RECIPE_MANAGER decision `DEC-RM-001` (2026-10-12) sets Android startup/debugging before UI redesign as the immediate priority. Preserve that later priority alongside the historical HTML-first phase; do not flatten the timeline or assume the HTML candidate was accepted merely because a matrix exists.

## Related memory

- `projects/RECIPE_MANAGER/DECISIONS.md`: `DEC-RM-001`, `DEC-RM-006`, `DEC-RM-008`, `DEC-RM-009`.
- `projects/RECIPE_MANAGER/events.jsonl`: `EVT-RM-20261001-005` (HTML-first phase) and `EVT-RM-20261002-001` (expiry-edit/Add Product report).
- `projects/RECIPE_MANAGER/SOURCE_COVERAGE.md`: source gaps and raw-export boundaries.
- `SOURCE_ARCHIVE_AUDIT_2026-10-12.md`: N99/B77 project identity boundary and mixed-scope source rules.
