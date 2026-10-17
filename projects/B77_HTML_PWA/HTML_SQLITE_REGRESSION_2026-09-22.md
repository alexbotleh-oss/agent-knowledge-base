# Historical HTML/SQLite regression evidence — 2026-09-22

## Scope and project attribution
This record captures HTML-contour incidents from the directly inspected user-supplied `conversations.json`. The user has explicitly clarified that **N99 is the Android APK** and **B77 is a separate HTML/WMA prototype/UI/logic and iPhone web version in `alexbotleh-oss/LK`**.

The source conversations themselves mostly discuss an HTML file and do not all name B77 explicitly. Therefore:
- **HTML-contour attribution:** high confidence.
- **Attribution of each early HTML conversation specifically to B77:** medium confidence, based on the user’s later explicit project boundary and the separate HTML project history.
- These reports are **not evidence of a defect in N99's Android APK**.
- The original HTML/database attachments were not included in the supplied ZIP; this is a source-message reconstruction, not a binary diff or runtime audit.

## Source conversations and chronology (UTC)

### 1. Ingredient matching and database path — 2026-09-22 17:35–18:36
- **Conversation:** `Нормализация ингредиентов`
- **Conversation ID:** `6ab2bc6a-1e38-83ed-9cd7-dec0af9324aa`
- At 17:35, the user specified canonical ingredient matching: generic/onion variants should resolve to repchaty onion while red/green onion remain distinct; rice categories should distinguish long-grain, round-grain and parboiled rice.
- At 17:38, the user asked to apply the change to the uploaded HTML file.
- At 18:05, the user added equivalence rules for sunflower/vegetable oil, non-chicken mince, pork/beef names, eggs, and related ingredient variants.
- At 18:14, the user reported false results: eggs present in Products were reported missing, while rice oil and rice flour were incorrectly reported as present.
- At 18:26, the user said database access had broken and requested behavior analogous to `index_db_path.html`.
- At 18:31, the user reiterated that ingredient matching must account for case, word order and grammatical case.

### 2. Repeated ingredient-logic request — 2026-09-22 17:51
- **Conversation:** `Исправление логики продуктов`
- **Conversation ID:** `6ab2c00e-82b8-83eb-afae-c73d36ece59c`
- Repeats the requested matching behavior across “Готовить”, “Рецепты” and “Продукты”. This is a second conversation record of the same requirement, not proof of a successful implementation.

### 3. Recipe list regression — 2026-09-22 18:44–18:50
- **Conversation:** `Продолжение разговора`
- **Conversation ID:** `6ab2cc8d-6770-83ed-b215-496904f80b77`
- A follow-up references `Что приготовить 22.htm` and the ingredient-normalization work.
- At 18:50, the user reported that the recipe list no longer populated. The source establishes the symptom, not its root cause.

### 4. Missing nutrition/deletion behavior — 2026-09-22 18:53–19:14
- **Conversation:** `Восстановление файлов чата`
- **Conversation ID:** `6ab2ce9f-df74-83eb-9412-8bf2174dca04`
- The user reported that the latest file no longer added recipes from the database and had lost nutrition display (КБЖУ). At 19:14, the user specifically reported loss of recipe deletion and kcal/100 g, protein, fat and carbohydrate display that existed in `index_db_path.html`.
- The exact broken file and reference file bytes are not in the supplied ZIP, so the regression can be recorded but not independently diffed here.

### 5. Recipe deletion and shopping flow — 2026-09-22 20:02–20:47
- **Conversation:** `Обновление рецептов и покупок`
- **Conversation ID:** `6ab2de4d-12f0-83ed-be6e-6212b0fdf4ad`
- The user asked for deleting one or all recipes, marking purchased items in an exported shopping-list file and sending the status back to Products for update/deletion.
- At 20:47, the user added equivalence requirements for wheat flour, butter and a pinch of salt, and requested matching recipe ingredients against the existing Products list.

## Facts vs. hypotheses
**Directly supported by source messages**
- HTML-file editing was requested.
- Ingredient normalization and explicit positive/negative matching cases were specified.
- The user reported database access, recipe-list population, nutrition display and recipe-deletion regressions.
- Shopping-list purchase marking and status return to Products were requested.

**Not established by the source JSON alone**
- Root cause of any regression.
- Whether a later candidate fixed any defect.
- Whether a specific HTML/SQLite file was the accepted baseline after these conversations.
- Whether all mentioned attachments were preserved in the supplied archive.
- Device/browser runtime behavior and persistence after deletion/import.

## Regression gate if B77 HTML work is resumed
1. Identify the accepted HTML baseline and compare the exact candidate against it.
2. Verify database selection/path behavior and recipe import/population.
3. Verify kcal/100 g, proteins, fats and carbohydrates display.
4. Verify delete-one and delete-all behavior and persistence after reload.
5. Verify Shopping purchase marking and status round-trip to Products.
6. Run ingredient positive and negative tests: onion variants; rice category resolution; eggs; oils; mince exclusion for chicken; flour; butter; salt pinch; case, word order and inflection.
7. Distinguish static inspection, browser runtime and persistence checks; do not report PASS from source inspection alone.

## Transfer rule
Ingredient normalization is a domain requirement that may be re-used in N99 only if separately accepted for that Android implementation. Its original event provenance belongs to this HTML-contour record; do not copy the B77 event IDs into N99.
