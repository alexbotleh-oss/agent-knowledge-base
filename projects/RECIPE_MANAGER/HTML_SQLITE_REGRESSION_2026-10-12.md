# HTML/SQLite regression evidence — 2026-10-12

## Scope
This record transfers only the available experience from the «Что приготовить» HTML/SQLite discussion. It does not diagnose or modify the application. No database write or APK build was performed for this memory-transfer task.

## Confirmed user reports
- The user attached several successive HTML candidates: `Что приготовить 22_готово_база_и_ингредиенты.htm`, `Что приготовить 22_исправлена_логика_ингредиентов(2).htm`, `Что приготовить 22_с_расширенной_нормализацией.htm`, a reference `index_db_path(5).html`, and `recipes(3).db`.
- The user said adding recipes from the database stopped working in the latest file and nutrition values disappeared.
- The user separately reported that the recipe-deletion function and display of kcal/100g, protein, fat, and carbohydrates from the reference had disappeared.
- The supplied reference HTML includes a recipe card rendering path for nutrition fields and a deletion path including API deletion for records with a database ID. This is evidence about the reference file only, not proof of the delivered candidate's runtime behavior.

## Ingredient normalization requirements
- Default `лук`, `белый лук`, `репчатый лук` resolve to pantry item `репчатый лук`; explicitly red and green onion stay distinct.
- Generic `рис` resolves to long-grain rice; `рис для плова` and explicitly parboiled rice resolve to parboiled rice.
- Normalize case, `ё/е`, grammatical forms and word order. Examples requested: `яйцо/яйца/яйцом`, `оливковое масло/масло оливковое/оливкового масла`.
- Avoid false prefix matches: `рис` must not match `рисовая мука` or `рисовое масло`.
- Preserve original wording in recipe display; normalization is for pantry lookup.

## Facts vs hypotheses
**Confirmed:** user-reported regressions and existence of the named attachments.  
**Not confirmed:** root cause of database-add/import failure or missing nutrition; whether the latest supplied HTML was runtime-tested after its latest link; whether the proposed local SQL.js deletion/download workflow actually persisted correctly. No complete diffs or runtime trace covering the candidates is available in this fragment.

## Required future regression gate if HTML work is reopened
1. Compare the exact target candidate with the accepted `index_db_path.html` reference.
2. Import/load recipes from SQLite and add database recipes to the displayed set.
3. Display kcal, protein, fat and carbohydrates per 100 g for records with values; handle missing values explicitly.
4. Delete a database recipe through the correct source (API or local in-memory SQLite) and verify persisted result separately.
5. Verify editing/save/reload and recipe data integrity.
6. Run normalization cases for onions, rice, eggs, oils, case, word order and inflections, plus negative cases preventing rice-flour/oil false matches.
7. Re-read the exact saved artifact and report static, runtime, and persistence checks separately.

Do not call an HTML candidate fixed based solely on JavaScript syntax, finding a function in source text, or generating a download link.

## Provenance and completeness
Source: messages and named attachments in the available project chat on 2026-10-12. The complete export of all related chats, the full binary history of each HTML/database candidate, and the exact candidate-to-candidate diffs are not available here. Status: **PARTIAL**. See event `EVT-20261012-014` and lesson `L-RM-019`.
