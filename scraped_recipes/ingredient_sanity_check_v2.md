# Ingredient Sanity Check v2 — New Dishes After Calendar Update
**Date:** 2026-03-12
**Trigger:** 7 produce items restricted from year-round to seasonal windows (Broccoli, Cauliflower, Lettuce, Swiss Chard, Kohlrabi, Corn, Eggplant).
**Pipeline objective:** 475.0 → 538.0 (+63). Covered produce: 34 → 41 items.

Only **newly-appeared dishes** are checked here (plus month-moved dishes re-verified). Previously-vetted dishes carry forward from v1.

---

## Newly Added Dishes (9 brand-new selections)

| # | Month | Recipe | Tags | Verdict |
|---|-------|--------|------|---------|
| N1 | Feb | Tofu and Chili Crisp Salad | Broccoli, Radish | ❌ |
| N2 | Mar | Garden Greens and Squash Salad | Butternut Squash, Kale, Lettuce | ⚠️ |
| N3 | Mar | Green Shakshuka | Asparagus | ✅ |
| N4 | Apr | Tara (Kavkazi Beef and Chard Soup) | Swiss Chard (Mangold) | ✅ |
| N5 | Aug | Fried Chicken Wings (Bubbie Chicken) | Corn | ❌ |
| N6 | Aug | Sesame Farro Salad | Avocado | ✅ |
| N7 | Sep | Fried Eggplant With Mint Dressing | Pomegranates, Eggplant | ✅ |
| N8 | Nov | Hand-Rolled Couscous | Butternut Squash, Kohlrabi | ✅ |
| N9 | Dec | Rhubarb and Strawberry Galette with Halva Cream | Oranges, Strawberries | ✅ |

---

## Detail

**N1 — Tofu and Chili Crisp Salad (Feb) — Broccoli, Radish ❌**
Ingredient: `2 cups radish or broccoli microgreens`
Both "broccoli" and "radish" fire on the word **microgreens** — young indoor sprouts, not the mature field vegetables. Microgreens are available year-round and do not reflect seasonal broccoli/radish availability. Pipeline does not flag "microgreens" as a preservation/processing context (it only flags dried/frozen/pickled/oil/etc.). **Both tags are false positives.**
Fix: add `NON_MATCH_OVERRIDE` entries for this recipe.

**N2 — Garden Greens and Squash Salad (Mar) — Butternut Squash ⚠️**
Ingredient: `1 medium delicata or acorn squash, around 1 lb.`
Pipeline matches via the alias `squash` (which is a keyword for Butternut Squash). The actual produce is delicata/acorn squash — autumn squashes with essentially the same seasonal window as butternut squash. The tag is botanically imprecise but seasonally correct. Displayed tag "Butternut Squash" is a slight misnomer.
Kale and Lettuce tags: `5 cups fresh garden greens (butter lettuce, arugula, kale or any combination)` — kale and lettuce both listed as explicit options, both fresh. Kale in Mar: ✅ ([1–3, 11–12]). Lettuce in Mar: ✅ ([11–12, 1–5]).

**N3 — Green Shakshuka (Mar) — Asparagus ✅**
`1 bunch asparagus, tough ends removed` — fresh. Asparagus in Mar: ✅ ([2, 3, 4]).

**N4 — Tara (Kavkazi Beef and Chard Soup) (Apr) — Swiss Chard (Mangold) ✅**
`1 pound hearty greens, such as mallow or Swiss chard` — Swiss chard listed as primary option, fresh. Swiss Chard in Apr: ✅ ([11, 12, 1–4]).

**N5 — Fried Chicken Wings / Bubbie Chicken (Aug) — Corn ❌**
Ingredients mentioning "corn":
- `2 cups cornflake crumbs` — `\bcorn\b` does NOT match "cornflake" (no word boundary after "corn"). Pipeline correctly skips this.
- `4-6 cups corn or vegetable oil` — `\bcorn\b` matches "corn" here. The word "oil" follows at character-offset 15–17 after "corn", just outside the 15-char PRESERVATION_AFTER window (`" or vegetable o"` is what the pipeline sees — "oil" is not fully within the window). The `corn oil` context is NOT detected as preserved.

Result: pipeline treats "corn" in "corn or vegetable oil" as **fresh seasonal corn**. This is wrong — corn oil is a refined cooking oil, not the fresh sweet corn vegetable.
Fix: add `NON_MATCH_OVERRIDE` for this recipe.

**N6 — Sesame Farro Salad (Aug) — Avocado ✅**
`1 avocado, cubed` — fresh. Avocado in Aug: ✅ ([1–5, 8–12]).

**N7 — Fried Eggplant With Mint Dressing (Sep) — Pomegranates, Eggplant ✅**
`2 medium eggplants, sliced into ¼-inch pieces` — fresh. Eggplant in Sep: ✅ ([5–10]).
`1 tablespoon pomegranate seeds for garnish` — fresh. Also contains `2 tablespoons pomegranate concentrate` — concentrate is caught by PRESERVATION_AFTER, but the fresh seeds constitute a fresh occurrence, so _is_preserved = False. Pipeline handling correct. Pomegranates in Sep: ✅.

**N8 — Hand-Rolled Couscous (Nov) — Butternut Squash, Kohlrabi ✅**
`1 ½ pounds pumpkin or butternut squash` — butternut squash explicitly named, fresh. Nov: ✅ ([1–4, 6–12]).
`1 kohlrabi, peeled and chopped` — fresh. Kohlrabi in Nov: ✅ ([11, 12, 1–4]).

**N9 — Rhubarb and Strawberry Galette with Halva Cream (Dec) — Oranges, Strawberries ✅**
`3 tablespoons freshly squeezed or store-bought orange juice` — juice = fresh. Oranges in Dec: ✅.
`2 cups strawberries, sliced` — fresh. Strawberries in Dec: ✅ ([1–3, 12]).
Note: `¾ pound rhubarb (about 4 large stalks)` — fresh rhubarb present but **Rhubarb is not in seasonal_produce.json** (calendar gap, same category as Figs from v1).

---

## Month-Moved Dishes (re-verified)

| Recipe | Old Month | New Month | Tags | Verdict |
|--------|-----------|-----------|------|---------|
| Gravlax | Feb | Jun | Grapefruit | ✅ Grapefruit in Jun: ✅ [1–6, 10–12] |
| Peach and Blueberry Kuchen | Aug | Jun | Peaches | ✅ Peaches in Jun: ✅ [5–11] |
| Lamb and Chestnut Plov | Dec | Jan | Chestnuts, Pomegranates | ✅ Both in Jan: ✅ |

---

## Fixes Required (2 hard fails → NON_MATCH_OVERRIDE)

### Fix 1 — tofu-and-chili-crisp-salad: exclude Broccoli + Radish
The only produce hit is "radish or broccoli microgreens" — not seasonal field produce.

### Fix 2 — fried-chicken-wings-bubbie-chicken: exclude Corn
The only corn mention is "corn or vegetable oil" — a cooking oil, not fresh sweet corn.

---

## Cumulative Sanity Status (v1 + v2)

| Total dishes | ✅ Pass | ⚠️ Soft flag | ❌ Hard fail |
|---|---|---|---|
| 36 | 31 | 3 | 2 |

Hard fails will be fixed via `NON_MATCH_OVERRIDE` in pipeline.py and pipeline re-run.
