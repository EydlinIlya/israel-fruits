# Metadata Audit — 36 Selected Dishes
**Date:** 2026-03-12
**Checks:** cooking time (standardized lowercase), region (single, classified if empty), diet/kashrut (single: Meat / Dairy / Pareve, reclassified if missing or wrong).

---

## Time normalization rules applied
A `_normalize_time()` function handles general cases:
- lowercase everything
- `"minutes"` → `"min"`, `"hours"` / `"hour"` → `"h"`
- `"2h"` → `"2 h"`, `"20min"` → `"20 min"`, `"1h 20m"` → `"1 h 20 min"`
- `"... and ..."` / `"..., plus ..."` / `"... plus ..."` → `"... + ..."`

Two special-case overrides added to `RECIPE_CORRECTIONS`:
- `hand-rolled-couscous`: `"1 h active + 4 h inactive + soaking"` → `"1 h active + 4 h inactive"` (drop vague "+ soaking" suffix)
- `pickled-nectarines-in-a-spiced-brine`: `"Prep time: 20 min + Ferment time: 48 h"` → `"20 min + 48 h ferment"` (strip verbose label prefixes)

---

## Region: empty → classified

| UID | Rationale | Assigned |
|-----|-----------|----------|
| `broccoli-soup-with-pasta-and-anchovy` | Romanesco broccoli + anchovy + pasta + pecorino — classic Italian profile | **Western Europe** |
| `garden-greens-and-squash-salad` | American-style composed salad | **North America** |
| `scotch-gravlax` | Gravlax = Scandinavian cure; Scotch whisky = Scottish — both Western European | **Western Europe** |
| `tzimmes-with-dates-pomegranate-and-mint` | Tzimmes is an Ashkenazi Jewish staple | **Eastern Europe** |
| `pomelo-candies` | Pomelos are an Israeli/Yemenite market staple; candied citrus fits Levantine tradition | **Middle East** |

(All other recipes already had a region; `_pick_region` in the pipeline reduces multi-region lists to one, prioritising North Africa > Middle East > first listed.)

---

## Diet / kashrut: full audit of all 36

`_pick_diet` strips everything except Meat / Dairy / Pareve and defaults to Pareve if none remain. Four recipes needed manual correction because the source data was wrong or absent:

| # | Month | Recipe | Pipeline output | Correction | Reason |
|---|-------|--------|----------------|------------|--------|
| 1 | Jan | Broccoli Soup with Pasta and Anchovy | Pareve | **Dairy** | `Pecorino, for serving` in ingredient list |
| 4 | Feb | Garden Greens and Squash Salad | Pareve | **Dairy** | `Ricotta salata, shaved (optional)` listed as ingredient |
| 33 | Nov | Arugula and Hazelnut Salad | Pareve | **Dairy** | `4 oz. shaved hard pecorino` — source wrongly tagged Pareve |
| 35 | Dec | Spanakopita (Spinach Pie) | Pareve | **Dairy** | `1¾ cups feta + 1 cup ricotta` — source had no kashrut tag; pipeline defaulted to Pareve |

All other 32 dishes: pipeline `_pick_diet` output accepted as correct.

---

## Full 36-dish table (post-fix values)

| # | Mon | Recipe | Time (fixed) | Region (fixed) | Diet (fixed) |
|---|-----|--------|-------------|----------------|--------------|
| 1 | Jan | Broccoli Soup with Pasta and Anchovy | 1 hour | Western Europe | **Dairy** |
| 2 | Jan | Triple Ginger Persimmon Loaf | 1 h 25 min | North America | Dairy |
| 3 | Jan | Opera-Style Chopped Salad | — | Middle East | Pareve |
| 4 | Feb | Garden Greens and Squash Salad | 40 min | North America | **Dairy** |
| 5 | Feb | Asparagus With Preserved Lemons and Herbs | 20 min | Middle East | Pareve |
| 6 | Feb | Chicken Thighs With Kumquats and Olives | — | Middle East | Meat |
| 7 | Mar | Msayer (Pickled Vegetables) | 30 min + 30 min pickling time | Middle East | Pareve |
| 8 | Mar | Hand-Rolled Couscous | 1 h active + 4 h inactive | North Africa | Meat |
| 9 | Mar | Rhubarb and Strawberry Galette with Halva Cream | 1 h + 30 min chilling time | North America | Dairy |
| 10 | Apr | Lettuce and Fennel Salad | 30 min | North Africa | Pareve |
| 11 | Apr | Venetian Charoset | 20 min | Western Europe | Pareve |
| 12 | Apr | Tara (Kavkazi Beef and Chard Soup) | 2 h | Middle East | Meat |
| 13 | May | Shaved Fennel and Orange Salad | 10 min | North Africa | Pareve |
| 14 | May | Spiced Apricot Cake | 1 h 20 min | Middle East | Dairy |
| 15 | May | Artichoke Heart Salad | 15 min | North Africa | Pareve |
| 16 | Jun | Gravlax | — | Western Europe | Pareve |
| 17 | Jun | Pastel de Choclo (South American Corn and Beef Casserole) | 1 h + 2 h inactive | South and Central America | Meat |
| 18 | Jun | Peach and Blueberry Kuchen | 3 h | Eastern Europe | Dairy |
| 19 | Jul | Meatballs With Cherries | 45 min | Middle East | Meat |
| 20 | Jul | Classic Mango Amba | — | Middle East | Pareve |
| 21 | Jul | Homemade Verjus | 3 days | Middle East | Pareve |
| 22 | Aug | Walnut and Vinegar Green Bean Lobio | 25 min | Eastern Europe | Pareve |
| 23 | Aug | Lox Bowl | 1 h 15 min | South Asia | Pareve |
| 24 | Aug | Watermelon and Bulgarian Cheese Salad With Mint | 15 min | Middle East | Dairy |
| 25 | Sep | Fried Eggplant With Mint Dressing | 45 min | Middle East | Pareve |
| 26 | Sep | Apple and Date Challah Bread Pudding | 1 h 45 min | Middle East | Dairy |
| 27 | Sep | Samsa (Pastries with Beef and Squash) | 1 h 45 min | Middle East | Meat |
| 28 | Oct | Khoresh e Beh (Lamb Stew With Quince and Dried Apricot) | 2 h | Middle East | Meat |
| 29 | Oct | Tzimmes With Dates, Pomegranate, and Mint | 40 min | Eastern Europe | Pareve |
| 30 | Oct | Pomelo Candies | — | Middle East | Pareve |
| 31 | Nov | Aliciotti Con Indivia (Anchovies Baked With Escarole) | 30–45 min | Western Europe | Pareve |
| 32 | Nov | Pickled Nectarines in a Spiced Brine | 20 min + 48 h ferment | Eastern Europe | Pareve |
| 33 | Nov | Arugula and Hazelnut Salad | 15 min | North America | **Dairy** |
| 34 | Dec | Lamb and Chestnut Plov (Pilaf) | 4 h | Eastern Europe | Meat |
| 35 | Dec | Spanakopita (Spinach Pie) | 2 h | Western Europe | **Dairy** |
| 36 | Dec | Guava Challah | 45 min active + 3 h 45 min inactive | South and Central America | Pareve |
