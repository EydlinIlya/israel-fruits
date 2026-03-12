"""
pipeline.py — Single-command seasonal recipe pipeline.

Phases:
  1. Score    – recipe × month matrix with fresh/preserved heuristics + overrides
  2. Optimize – assign 3 recipes/month (no duplicates), maximise quality + variety
  3. Generate – build MONTH_DISHES JS block and patch index.html in place

Usage:
  python scraped_recipes/pipeline.py
"""

import json
import random
import re
import time
from pathlib import Path

# ============================================================================
# PATHS
# ============================================================================

BASE          = Path(__file__).parent.parent
PRODUCE_FILE  = BASE / "seasonal_produce.json"
ALIASES_FILE  = BASE / "scraped_recipes" / "produce_aliases.json"
RECIPES_FILE  = BASE / "scraped_recipes" / "all_recipes.json"
INDEX_HTML    = BASE / "index.html"
OUT_SNIPPET   = BASE / "scraped_recipes" / "month_dishes_snippet.js"
OUT_SELECTION = BASE / "scraped_recipes" / "month_selection.json"   # written for reference / audit

# ============================================================================
# CONFIG  — all tunable parameters and overrides in one place
# ============================================================================

# ── Scoring ──────────────────────────────────────────────────────────────────

MIN_IN_SEASON = 1    # minimum non-yr-round in-season matches to qualify
OOS_PENALTY   = 10   # subtracted per out-of-season non-preserved item

# Recipes excluded from the pipeline entirely.
BLACKLISTED_UIDS: set = set()   # harosets moved to HAROSET_UIDS below

# Haroset / charoset recipes — eligible only for April (month 4), max 1 selected.
HAROSET_UIDS: set = {
    "venetian-charoset",
    "surinamese-charoset",
    "maine-charoset",
    "yemenite-charoset",
    "afghan-haroset",
    "charoset-mike",
    "persian-charoset-with-pear-apple-banana-and-dates",
    "apple-and-asian-pear-charoset",
    "charoset-with-dates-pistachios-and-rose-water1",
}
HAROSET_MONTH = 4   # April only
MAX_HAROSET   = 1   # at most one haroset across all 36 slots

# Per-recipe produce items that are ALWAYS treated as fresh, even if the
# preservation detector would flag them (e.g. charoset with dried dates —
# dried dates ARE the defining seasonal ingredient there).
FRESH_OVERRIDE: dict[str, set] = {
    # (Dates removed from charoset — they are dried, not fresh seasonal produce)
}

# Per-recipe produce items to EXCLUDE from matching entirely, regardless of
# what the keyword / preservation detector finds.  Use for cases where the
# ingredient text mentions the produce name but in a non-produce context:
#   • avocado oil  (oil for frying, not the fresh fruit)
#   • grape juice  (juice not caught by PRESERVATION_AFTER by design — but
#                   store-bought juice is not fresh seasonal produce)
#   • fennel seeds (dried spice; "fennel" keyword fires but it's not fresh bulb)
#   • dried apricots appearing twice so one occurrence escapes the detector
#   • canned pineapple
#   • "mango tilapia" — fish species name, not the mango fruit
NON_MATCH_OVERRIDE: dict[str, set] = {
    "menenas-shortbread-filled-with-dates-and-walnuts":      {"Dates"},
    "charoset-with-dates-pistachios-and-rose-water1":        {"Dates", "Grapes"},
    "rojitos-fritos-de-pessah-passover-fish-escabeche":      {"Fennel"},
    "artichoke-confit-challah-with-parmesan":                {"Fennel"},
    "yebra-stuffed-grape-leaves-with-apricots":              {"Apricots", "Grapes"},
    "fried-st.-peters-fish-musht":                           {"Mangoes"},
    "kachori-spiced-pea-dumpling":                           {"Fennel"},
    "apple-strudel":                                         {"Pineapple"},
    "ejjeh-syrian-vegetable-fritters":                       {"Avocado"},
    # Grapes = jarred brine-packed grape leaves — preserved
    "dolma-vegetarian-stuffed-grape-leaves":                 {"Grapes"},
    # Fennel = fennel seed inside Merguez spice blend — dried spice
    "eggplant-stuffed-with-lamb":                            {"Fennel"},
    # Limes = makrut lime leaves (Citrus hystrix) — different species from seasonal Limes
    "nasi-tumpeng-celebratory-indonesian-rice":              {"Limes"},
    # Broccoli + Radish = broccoli/radish microgreens only — indoor sprouts, not seasonal field produce
    "tofu-and-chili-crisp":                                  {"Broccoli", "Radish"},
    # Corn = corn oil ("4-6 cups corn or vegetable oil") — cooking oil, not fresh sweet corn
    "fried-chicken-wings-bubbie-chicken":                    {"Corn"},
}

# Keywords that appear BEFORE a produce word indicating a preserved form.
PRESERVATION_BEFORE = re.compile(
    r"\b(dried|candied|preserved|frozen|pickled|canned|bottled|powdered|"
    r"crystallised|crystallized)\b"
)

# Keywords that appear AFTER a produce word indicating a processed product.
# e.g. "avocado oil", "pomegranate molasses", "date syrup", "orange blossom water"
# NOTE: juice / zest / peel / rind deliberately excluded — "fresh lemon juice"
# or "orange zest" still require fresh fruit.
PRESERVATION_AFTER = re.compile(
    r"\b(oil|oils|blossom|blossoms|molasses|syrup|syrups|"
    r"paste|jam|jams|extract|extracts|"
    r"sauce|sauces|concentrate|concentrates|powder|powders|cider|"
    r"vinegar|vinegars|butter|spread|purée|puree|coulis)\b"
)

# ── Bonuses / penalties ───────────────────────────────────────────────────────

REGION_BONUS_REGIONS = {"middle east", "north africa", "israel", "levant"}
REGION_BONUS         = 1

HOLIDAY_MONTHS: dict[str, list] = {
    "passover":      [4],
    "purim":         [3],
    "shavuot":       [6],
    "rosh hashana":  [9, 10],
    "rosh hashanah": [9, 10],
    "yom kippur":    [9, 10],
    "sukkot":        [9, 10],
    "hanukkah":      [12],
    "chanukah":      [12],
    "tu bishvat":    [1, 2],
    "tu b'shvat":    [1, 2],
    "shabbat":       list(range(1, 13)),
    "sabbath":       list(range(1, 13)),
}

HOLIDAY_BONUS_PTS: dict[str, int] = {
    "passover": 2, "purim": 2, "shavuot": 2,
    "rosh hashana": 2, "rosh hashanah": 2, "yom kippur": 2,
    "sukkot": 2, "hanukkah": 2, "chanukah": 2,
    "tu bishvat": 2, "tu b'shvat": 2,
    "shabbat": 1, "sabbath": 1,
}

ALWAYS_OK_HOLIDAYS      = {"shabbat", "sabbath"}
HOLIDAY_MISMATCH_PENALTY = 5

# ── Optimisation ─────────────────────────────────────────────────────────────

SLOTS            = 3    # recipes per month
DISH_PENALTY     = 3    # subtracted per extra same-type recipe within a month
COVERAGE_WEIGHT  = 8    # per unique produce item covered globally across all 36
DIVERSITY_WEIGHT = 2    # per unique produce item per month
N_RESTARTS       = 80   # random restarts for local search (more → better, slower)
RANDOM_SEED      = 42

# ── Misc ──────────────────────────────────────────────────────────────────────

# Alias tokens to skip when auto-generating keyword variants from produce names.
SKIP_ALIASES = {"nana", "batata"}

BASE_URL = "https://www.jewishfoodsociety.org/recipes/"

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Per-recipe overrides applied in build_js AFTER _pick_region / _pick_diet / time normalisation.
# Keys: "region" (list), "diet" (list), "time" (str).
RECIPE_CORRECTIONS: dict[str, dict] = {
    # ── Region: classify recipes with empty region_tags ──────────────────────
    "broccoli-soup-with-pasta-and-anchovy":            {"region": ["Western Europe"],        "diet": ["Dairy"]},   # pecorino for serving
    "garden-greens-and-squash-salad":                  {"region": ["North America"],          "diet": ["Dairy"]},   # ricotta salata listed
    "scotch-gravlax":                                  {"region": ["Western Europe"]},
    "tzimmes-with-dates-pomegranate-and-mint":         {"region": ["Eastern Europe"]},
    "pomelo-candies":                                  {"region": ["Middle East"]},
    # ── Diet: fix source misclassifications ──────────────────────────────────
    "arugula-and-hazelnut-salad":                      {"diet": ["Dairy"]},   # 4 oz pecorino; source wrongly Pareve
    "spanakopita-spinach-pie":                         {"diet": ["Dairy"]},   # feta + ricotta; source had no kashrut tag
    # ── Time: special cases not handled by general normalisation ─────────────
    "hand-rolled-couscous":                            {"time": "1 h active + 4 h inactive"},
    "pickled-nectarines-in-a-spiced-brine":            {"time": "20 min + 48 h ferment"},
}

# ============================================================================
# PHASE 1: SCORE
# ============================================================================

def _parse_produce_name(name: str) -> list[str]:
    """Turn produce display name into lowercase keyword variants."""
    keywords: list[str] = []
    for part in [p.strip() for p in name.split(" / ")]:
        m = re.match(r"^(.+?)\s*\((.+?)\)\s*$", part)
        if m:
            main_kw  = m.group(1).strip().lower()
            alias_kw = m.group(2).strip().lower()
            keywords.append(main_kw)
            if alias_kw not in SKIP_ALIASES:
                keywords.append(alias_kw)
        else:
            keywords.append(part.strip().lower())
    extras: list[str] = []
    for kw in keywords:
        if "-" in kw or " " in kw:
            last = kw.replace("-", " ").split()[-1]
            if len(last) > 3 and last not in keywords and last not in extras:
                extras.append(last)
    keywords.extend(extras)
    seen: set = set()
    return [k for k in keywords if not (k in seen or seen.add(k))]  # type: ignore[func-returns-value]


def load_produce(produce_file: Path, aliases_file: Path) -> dict:
    """
    Returns produce_kw dict:
      {name: {keywords, months(set), is_yr(bool), rarity_pts(int)}}
    Keywords come from produce_aliases.json when present, else auto-generated.
    """
    with open(produce_file, encoding="utf-8") as f:
        produce_data = json.load(f)

    aliases: dict[str, list[str]] = {}
    if aliases_file.exists():
        with open(aliases_file, encoding="utf-8") as f:
            raw = json.load(f)
        for cat in ("fruits", "vegetables", "herbs"):
            for name, kws in raw.get(cat, {}).items():
                aliases[name] = [k.lower() for k in kws if isinstance(k, str)]

    produce_kw: dict = {}
    for cat in ("fruits", "vegetables", "herbs"):
        for item in produce_data.get(cat, []):
            name   = item["name"]
            months = set(item["months"])
            mc     = len(months)
            kws    = aliases.get(name, _parse_produce_name(name))
            produce_kw[name] = {
                "keywords":   kws,
                "months":     months,
                "is_yr":      mc == 12,
                "rarity_pts": 1 if mc < 12 else 0,
            }
    return produce_kw


def _extract_ing_text(recipe: dict) -> str:
    parts: list[str] = []
    for group in recipe.get("ingredients", []):
        for item in group.get("list", []):
            t = item.get("text", "")
            if t:
                parts.append(t)
    return " ".join(parts).lower()


def _is_preserved(text: str, keywords: list[str]) -> bool:
    """
    True iff every occurrence of every keyword in text appears in a
    preserved/processed context (dried before, or molasses/syrup/… after).
    A single fresh occurrence → returns False.
    """
    for kw in keywords:
        p = re.compile(r"\b" + re.escape(kw) + r"\b")
        for m in p.finditer(text):
            before = text[max(0, m.start() - 20): m.start()]
            after  = text[m.end(): m.end() + 15]
            if not (PRESERVATION_BEFORE.search(before) or
                    PRESERVATION_AFTER.search(after)):
                return False   # found a fresh occurrence
    return True   # all occurrences are preserved / no occurrence found


def score_all(recipes: list, produce_kw: dict) -> tuple[dict, dict]:
    """
    Phase 1 core: score every recipe × every month.

    Returns:
      full_matrix  — {uid: {month(int): score(int)}}
      produce_map  — {uid: {month(int): [seasonal_non_yr_tag_names]}}
                     Keys only present when score > 0.
    """
    kw_patterns: dict[str, list] = {
        name: [re.compile(r"\b" + re.escape(kw) + r"\b") for kw in info["keywords"]]
        for name, info in produce_kw.items()
    }

    ing_texts: dict[str, str] = {r["uid"]: _extract_ing_text(r) for r in recipes}

    # Pre-compute per-recipe: which produce matched + is it preserved?
    # matched_cache[uid][name] = True(preserved) | False(fresh)
    matched_cache: dict[str, dict[str, bool]] = {}
    for recipe in recipes:
        uid = recipe["uid"]
        if uid in BLACKLISTED_UIDS:
            continue
        text            = ing_texts[uid]
        fresh_overrides = FRESH_OVERRIDE.get(uid, set())
        non_matches     = NON_MATCH_OVERRIDE.get(uid, set())
        matched: dict[str, bool] = {}
        for name, info in produce_kw.items():
            if name in non_matches:
                continue   # explicitly excluded — skip regardless of keyword hit
            if any(p.search(text) for p in kw_patterns[name]):
                preserved = False if name in fresh_overrides else _is_preserved(text, info["keywords"])
                matched[name] = preserved
        matched_cache[uid] = matched

    full_matrix: dict[str, dict[int, int]] = {}
    produce_map: dict[str, dict[int, list]] = {}

    for recipe in recipes:
        uid = recipe["uid"]
        if uid not in matched_cache:
            continue

        meta     = recipe.get("_meta", {})
        holidays = [h.lower().strip() for h in meta.get("holidays_tags", [])]
        r_bonus  = REGION_BONUS if (
            {r.lower() for r in meta.get("region_tags", [])} & REGION_BONUS_REGIONS
        ) else 0

        month_scores: dict[int, int] = {}

        for month in range(1, 13):
            in_season:   list[str] = []
            oos_penalty: int       = 0

            for name, is_pres in matched_cache[uid].items():
                info = produce_kw[name]
                if month in info["months"]:
                    if not is_pres:
                        in_season.append(name)
                elif not info["is_yr"] and not is_pres:
                    oos_penalty += OOS_PENALTY

            # Require at least MIN_IN_SEASON non-yr-round seasonal matches
            seasonal_count = sum(1 for n in in_season if not produce_kw[n]["is_yr"])
            if seasonal_count < MIN_IN_SEASON:
                month_scores[month] = 0
                continue

            ing_score = sum(produce_kw[n]["rarity_pts"] for n in in_season)
            if ing_score == 0:
                month_scores[month] = 0
                continue

            # Holiday bonuses / mismatch penalties
            h_bonus = h_mismatch = 0
            for tag in holidays:
                months_for = HOLIDAY_MONTHS.get(tag)
                if months_for:
                    if month in months_for:
                        h_bonus += HOLIDAY_BONUS_PTS.get(tag, 1)
                    elif tag not in ALWAYS_OK_HOLIDAYS:
                        h_mismatch -= HOLIDAY_MISMATCH_PENALTY

            score = max(ing_score - oos_penalty + r_bonus + h_bonus + h_mismatch, 0)
            month_scores[month] = score

            if score > 0:
                seasonal_tags = [n for n in in_season if not produce_kw[n]["is_yr"]]
                produce_map.setdefault(uid, {})[month] = seasonal_tags

        # Harosets may only appear in April
        if uid in HAROSET_UIDS:
            for m in list(month_scores):
                if m != HAROSET_MONTH:
                    month_scores[m] = 0
            if uid in produce_map:
                produce_map[uid] = {
                    k: v for k, v in produce_map[uid].items()
                    if k == HAROSET_MONTH
                }

        if any(v > 0 for v in month_scores.values()):
            full_matrix[uid] = month_scores

    return full_matrix, produce_map


# ============================================================================
# PHASE 2: OPTIMIZE
# ============================================================================

def _compute_mv(month: int, uid_list: list, full_matrix: dict, dish_types: dict) -> int:
    total = sum(full_matrix.get(uid, {}).get(month, 0) for uid in uid_list)
    type_counts: dict = {}
    for uid in uid_list:
        t = dish_types.get(uid, "Other")
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in type_counts.items():
        if c > 1:
            total -= DISH_PENALTY * (c - 1)
    return total


def _objective(mv_cache: dict, month_produce: dict, global_coverage: int) -> float:
    quality   = sum(max(mv, 0) for mv in mv_cache.values())
    diversity = DIVERSITY_WEIGHT * sum(len(s) for s in month_produce.values())
    coverage  = COVERAGE_WEIGHT * global_coverage
    return quality + diversity + coverage


def _greedy_init(full_matrix: dict, dish_types: dict,
                 month_order: list, produce_for: dict) -> dict:
    used: set        = set()
    assignments: dict = {}
    haroset_used: int = 0

    for month in month_order:
        pos_cands = [uid for uid in full_matrix
                     if uid not in used and full_matrix[uid].get(month, 0) > 0]
        if len(pos_cands) < SLOTS:
            extras = [uid for uid in full_matrix
                      if uid not in used and uid not in set(pos_cands)]
            random.shuffle(extras)
            all_cands = pos_cands + extras
        else:
            all_cands = pos_cands

        selected: list          = []
        type_counts: dict       = {}
        covered_this_month: set = set()
        remaining               = list(all_cands)

        while len(selected) < SLOTS and remaining:
            best_eff = -1e18
            best_uid = None
            for uid in remaining:
                # Haroset cap: skip if limit reached
                if uid in HAROSET_UIDS and haroset_used >= MAX_HAROSET:
                    continue
                base     = full_matrix.get(uid, {}).get(month, 0)
                new_prod = len(
                    set(produce_for.get(uid, {}).get(month, [])) - covered_this_month
                )
                eff = base + DIVERSITY_WEIGHT * new_prod
                if type_counts.get(dish_types.get(uid, "Other"), 0) >= 2:
                    eff -= 1000  # soft penalty: prefer dish-type diversity
                if eff > best_eff:
                    best_eff = eff
                    best_uid = uid
            if best_uid is None:
                break
            selected.append(best_uid)
            if best_uid in HAROSET_UIDS:
                haroset_used += 1
            t = dish_types.get(best_uid, "Other")
            type_counts[t] = type_counts.get(t, 0) + 1
            covered_this_month |= set(produce_for.get(best_uid, {}).get(month, []))
            remaining.remove(best_uid)

        for uid in selected:
            used.add(uid)
        assignments[month] = list(selected[:SLOTS])

    return assignments


def _local_search(assignments: dict, full_matrix: dict, dish_types: dict,
                  produce_for: dict, max_iters: int = 500) -> tuple[dict, float]:
    asgn = {m: list(v) for m, v in assignments.items()}
    mv   = {m: _compute_mv(m, asgn[m], full_matrix, dish_types) for m in asgn}
    used = {uid for lst in asgn.values() for uid in lst}

    # Initialise produce tracking
    month_produce: dict[int, set] = {}
    produce_count: dict[str, int] = {}
    for m in asgn:
        mp: set = set()
        for uid in asgn[m]:
            items = produce_for.get(uid, {}).get(m, [])
            mp.update(items)
            for item in items:
                produce_count[item] = produce_count.get(item, 0) + 1
        month_produce[m] = mp
    global_coverage = sum(1 for c in produce_count.values() if c > 0)

    haroset_used = sum(1 for lst in asgn.values() for uid in lst if uid in HAROSET_UIDS)

    all_uids = list(full_matrix.keys())
    unasgn   = sorted(
        [uid for uid in all_uids if uid not in used],
        key=lambda u: sum(full_matrix[u].values()),
        reverse=True,
    )
    months = list(asgn.keys())

    for _iter in range(max_iters):
        best_delta = 1e-9
        best_move  = None

        # ── Replace-swaps ────────────────────────────────────────────────────
        for month in months:
            old_qual = max(mv[month], 0)
            lst      = asgn[month]
            for i, old_uid in enumerate(lst):
                old_prod  = set(produce_for.get(old_uid, {}).get(month, []))
                other_prod: set = set()
                for j, u in enumerate(lst):
                    if j != i:
                        other_prod |= set(produce_for.get(u, {}).get(month, []))

                for new_uid in unasgn:
                    # Haroset cap: replacing a non-haroset with a haroset when limit reached
                    if (new_uid in HAROSET_UIDS and old_uid not in HAROSET_UIDS
                            and haroset_used >= MAX_HAROSET):
                        continue
                    lst[i]    = new_uid
                    new_mv    = _compute_mv(month, lst, full_matrix, dish_types)
                    lst[i]    = old_uid
                    delta_qual = max(new_mv, 0) - old_qual

                    new_prod  = set(produce_for.get(new_uid, {}).get(month, []))
                    new_mp    = other_prod | new_prod
                    delta_div = DIVERSITY_WEIGHT * (len(new_mp) - len(month_produce[month]))

                    only_old  = old_prod - new_prod
                    only_new  = new_prod - old_prod
                    g_lost    = sum(1 for it in only_old if produce_count.get(it, 0) == 1)
                    g_gained  = sum(1 for it in only_new if produce_count.get(it, 0) == 0)
                    delta_cov = COVERAGE_WEIGHT * (g_gained - g_lost)

                    total = delta_qual + delta_div + delta_cov
                    if total > best_delta:
                        best_delta = total
                        best_move  = ("rep", month, i, old_uid, new_uid,
                                      new_mv, new_mp, g_gained - g_lost)

        # ── Cross-month swaps ────────────────────────────────────────────────
        for a in range(len(months)):
            for b in range(a + 1, len(months)):
                m1, m2   = months[a], months[b]
                lst1, lst2 = asgn[m1], asgn[m2]
                old_qual = max(mv[m1], 0) + max(mv[m2], 0)

                for k1, uid1 in enumerate(lst1):
                    for k2, uid2 in enumerate(lst2):
                        lst1[k1], lst2[k2] = uid2, uid1
                        new_mv1 = _compute_mv(m1, lst1, full_matrix, dish_types)
                        new_mv2 = _compute_mv(m2, lst2, full_matrix, dish_types)
                        lst1[k1], lst2[k2] = uid1, uid2
                        delta_qual = (max(new_mv1, 0) + max(new_mv2, 0)) - old_qual

                        old1 = set(produce_for.get(uid1, {}).get(m1, []))
                        old2 = set(produce_for.get(uid2, {}).get(m2, []))
                        new1 = set(produce_for.get(uid2, {}).get(m1, []))
                        new2 = set(produce_for.get(uid1, {}).get(m2, []))

                        oth1: set = set()
                        for j, u in enumerate(lst1):
                            if j != k1:
                                oth1 |= set(produce_for.get(u, {}).get(m1, []))
                        new_mp1 = oth1 | new1

                        oth2: set = set()
                        for j, u in enumerate(lst2):
                            if j != k2:
                                oth2 |= set(produce_for.get(u, {}).get(m2, []))
                        new_mp2 = oth2 | new2

                        delta_div = DIVERSITY_WEIGHT * (
                            (len(new_mp1) - len(month_produce[m1])) +
                            (len(new_mp2) - len(month_produce[m2]))
                        )

                        affected = old1 | old2 | new1 | new2
                        g_net    = 0
                        for item in affected:
                            old_c = produce_count.get(item, 0)
                            chg   = ((1 if item in new1 else 0) +
                                     (1 if item in new2 else 0) -
                                     (1 if item in old1 else 0) -
                                     (1 if item in old2 else 0))
                            new_c = old_c + chg
                            if old_c == 0 and new_c > 0:
                                g_net += 1
                            elif old_c > 0 and new_c == 0:
                                g_net -= 1
                        delta_cov = COVERAGE_WEIGHT * g_net

                        total = delta_qual + delta_div + delta_cov
                        if total > best_delta:
                            best_delta = total
                            best_move  = ("cross", m1, k1, uid1, new_mv1,
                                          m2, k2, uid2, new_mv2,
                                          new_mp1, new_mp2, g_net)

        if best_move is None:
            break  # local optimum reached

        # ── Apply best move ──────────────────────────────────────────────────
        if best_move[0] == "rep":
            _, month, i, old_uid, new_uid, new_mv_val, new_mp, g_net = best_move
            for it in produce_for.get(old_uid, {}).get(month, []):
                produce_count[it] = produce_count.get(it, 0) - 1
            for it in produce_for.get(new_uid, {}).get(month, []):
                produce_count[it] = produce_count.get(it, 0) + 1
            global_coverage      += g_net
            month_produce[month]  = new_mp
            asgn[month][i]        = new_uid
            mv[month]             = new_mv_val
            if old_uid in HAROSET_UIDS: haroset_used -= 1
            if new_uid in HAROSET_UIDS: haroset_used += 1
            used.discard(old_uid)
            used.add(new_uid)
            unasgn.remove(new_uid)
            s   = sum(full_matrix[old_uid].values())
            pos = next((j for j, u in enumerate(unasgn)
                        if sum(full_matrix[u].values()) <= s), len(unasgn))
            unasgn.insert(pos, old_uid)
        else:
            _, m1, k1, uid1, new_mv1, m2, k2, uid2, new_mv2, new_mp1, new_mp2, g_net = best_move
            for it in produce_for.get(uid1, {}).get(m1, []):
                produce_count[it] = produce_count.get(it, 0) - 1
            for it in produce_for.get(uid2, {}).get(m2, []):
                produce_count[it] = produce_count.get(it, 0) - 1
            for it in produce_for.get(uid2, {}).get(m1, []):
                produce_count[it] = produce_count.get(it, 0) + 1
            for it in produce_for.get(uid1, {}).get(m2, []):
                produce_count[it] = produce_count.get(it, 0) + 1
            global_coverage  += g_net
            month_produce[m1] = new_mp1
            month_produce[m2] = new_mp2
            asgn[m1][k1]      = uid2
            asgn[m2][k2]      = uid1
            mv[m1]            = new_mv1
            mv[m2]            = new_mv2

    return asgn, _objective(mv, month_produce, global_coverage)


def optimise(full_matrix: dict, dish_types: dict, produce_for: dict) -> dict:
    random.seed(RANDOM_SEED)
    months    = list(range(1, 13))
    best_asgn = None
    best_obj  = -1.0

    print(f"  Running {N_RESTARTS} restarts...")
    t0 = time.time()

    for restart in range(N_RESTARTS):
        month_order = months.copy()
        random.shuffle(month_order)
        asgn = _greedy_init(full_matrix, dish_types, month_order, produce_for)

        # Ensure all 12 months have SLOTS recipes (pad with any unassigned)
        used = {uid for lst in asgn.values() for uid in lst}
        for m in months:
            if m not in asgn:
                cands = [uid for uid in full_matrix if uid not in used]
                random.shuffle(cands)
                asgn[m] = cands[:SLOTS]
                used.update(asgn[m])

        asgn, obj = _local_search(asgn, full_matrix, dish_types, produce_for)

        if obj > best_obj:
            best_obj  = obj
            best_asgn = {m: list(v) for m, v in asgn.items()}
            print(f"    restart {restart+1:3d}/{N_RESTARTS}  new best = {obj:.1f}")

    print(f"  Done in {time.time()-t0:.1f}s  objective = {best_obj:.1f}")
    return best_asgn  # type: ignore[return-value]


# ============================================================================
# PHASE 3: GENERATE
# ============================================================================

def _js_escape(s: str) -> str:
    return (s.replace("\\", "\\\\")
             .replace('"', '\\"')
             .replace("\n", " ")
             .replace("\r", "")
             .replace("\xa0", " "))


def _normalize_time(s: str) -> str:
    """Lowercase and standardise common time-string patterns."""
    if not s:
        return s
    s = s.strip().lower()
    s = re.sub(r"\bminutes\b", "min", s)
    s = re.sub(r"\bhours\b",   "h",   s)
    s = re.sub(r"\bhour\b",    "h",   s)
    # "2h" → "2 h",  "20min" → "20 min"
    s = re.sub(r"(\d)h\b",   r"\1 h",   s)
    s = re.sub(r"(\d)min\b", r"\1 min", s)
    # "40m" (bare m, not already "min") → "40 min"
    s = re.sub(r"(\d)m\b(?!in)", r"\1 min", s)
    # connectors: ", plus" / " plus " / " and " → " + "
    s = re.sub(r",?\s+plus\s+", " + ", s)
    s = re.sub(r"\s+and\s+",   " + ", s)
    s = re.sub(r" +", " ", s)
    return s.strip()


def _pick_region(region_tags: list[str]) -> list[str]:
    """Return a single-element region list, priority: North Africa > Middle East > first."""
    if not region_tags:
        return []
    rl = [r.lower() for r in region_tags]
    if any("north africa" in r for r in rl):
        return ["North Africa"]
    if any("middle east" in r for r in rl):
        return ["Middle East"]
    return [region_tags[0]]


def _pick_diet(diet_raw: list[str]) -> list[str]:
    """
    Return cleaned diet list:
      • Only Meat / Dairy / Pareve (kashrut)
      • If none of those, fall back to Vegan or Vegetarian (one only)
      • Remove Vegetarian if Vegan is present
      • Drop Kosher for Passover, Gluten Free, and anything else
    """
    kashrut = {"Meat", "Dairy", "Pareve"}
    # Strip whitespace — raw tags sometimes come in as "Meat " with trailing space
    diet_raw = [d.strip() for d in diet_raw]
    diet = [d for d in diet_raw if d in kashrut]
    if "Vegan" in diet_raw and "Vegetarian" in diet:
        diet = [d for d in diet if d != "Vegetarian"]
    if not diet:
        # Vegan/Vegetarian dishes have no forbidden ingredients → Pareve
        return ["Pareve"]
    return diet


def build_js(assignments: dict, produce_for: dict,
             recipe_map: dict, year_round_set: set) -> str:
    """Build the full MONTH_DISHES JS literal."""

    def js_arr(lst: list) -> str:
        return "[" + ", ".join(f'"{_js_escape(x)}"' for x in lst) + "]"

    lines = ["const MONTH_DISHES = {"]

    for m in range(1, 13):
        entries: list[str] = []
        for uid in assignments[m]:
            recipe    = recipe_map.get(uid, {})
            meta      = recipe.get("_meta", {})
            name      = recipe.get("title", uid)
            time_str  = recipe.get("timeEstimate", "") or ""
            url       = BASE_URL + uid

            # Tags: from produce_map for this (uid, month), year-round items removed
            tags = [t for t in produce_for.get(uid, {}).get(m, [])
                    if t not in year_round_set]

            dish_tags = meta.get("dish_tags", [])
            dish_type = _js_escape(dish_tags[0] if dish_tags else "Other")
            region    = _pick_region(meta.get("region_tags", []))
            diet      = _pick_diet(meta.get("diet_tags", []))

            # Apply per-recipe corrections (region, diet, time)
            time_str = _normalize_time(time_str)
            corr = RECIPE_CORRECTIONS.get(uid, {})
            if "region" in corr:
                region = corr["region"]
            if "diet" in corr:
                diet = corr["diet"]
            if "time" in corr:
                time_str = corr["time"]

            entry = (
                f'    {{name:"{_js_escape(name)}",'
                f'time:"{_js_escape(time_str)}",'
                f'dish:"{dish_type}",'
                f'region:{js_arr(region)},'
                f'diet:{js_arr(diet)},'
                f'tags:{js_arr(tags)},'
                f'url:"{url}"}}'
            )
            entries.append(entry)

        lines.append(f"  {m}:[")
        lines.append(",\n".join(entries))
        lines.append("  ]," if m < 12 else "  ]")

    lines.append("};")
    return "\n".join(lines)


def patch_index_html(index_path: Path, js_content: str) -> None:
    with open(index_path, encoding="utf-8") as f:
        html = f.read()
    pattern = re.compile(r"const MONTH_DISHES = \{.*?\};", re.DOTALL)
    if not pattern.search(html):
        raise ValueError("MONTH_DISHES block not found in index.html")
    new_html = pattern.sub(js_content, html, count=1)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_html)


# ============================================================================
# ENTRYPOINT
# ============================================================================

def main() -> None:
    from calendar import month_abbr

    # ── Load data ─────────────────────────────────────────────────────────────
    print("Loading produce data...")
    produce_kw    = load_produce(PRODUCE_FILE, ALIASES_FILE)
    year_round_set = {name for name, info in produce_kw.items() if info["is_yr"]}
    seasonal_set   = {name for name, info in produce_kw.items() if not info["is_yr"]}
    print(f"  {len(produce_kw)} produce items  "
          f"({len(seasonal_set)} seasonal, {len(year_round_set)} year-round)")

    print("Loading recipes...")
    with open(RECIPES_FILE, encoding="utf-8") as f:
        recipes = json.load(f)
    recipe_map: dict = {r["uid"]: r for r in recipes}
    print(f"  {len(recipes)} recipes  ({len(BLACKLISTED_UIDS)} blacklisted)")

    # Build dish_types map
    dish_types: dict = {}
    for recipe in recipes:
        uid      = recipe["uid"]
        meta     = recipe.get("_meta", {})
        dt       = (meta.get("dish_tags") or ["Other"])[0]
        dish_types[uid] = dt

    # ── Phase 1: Score ────────────────────────────────────────────────────────
    print("\n-- Phase 1: Scoring ------------------------------------------")
    full_matrix, produce_for = score_all(recipes, produce_kw)
    print(f"  {len(full_matrix)} recipes scored in at least one month")
    total_entries = sum(len(v) for v in produce_for.values())
    print(f"  {total_entries} (uid, month) entries with tags in produce_map")

    # ── Phase 2: Optimize ─────────────────────────────────────────────────────
    print("\n-- Phase 2: Optimising ---------------------------------------")
    assignments = optimise(full_matrix, dish_types, produce_for)

    # Print assignment summary
    print("\nFinal assignment:")
    all_global: set = set()
    for m in range(1, 13):
        uid_list = assignments[m]
        mv_val   = _compute_mv(m, uid_list, full_matrix, dish_types)
        mp: set  = set()
        for uid in uid_list:
            mp |= set(produce_for.get(uid, {}).get(m, []))
        all_global |= mp
        row = " | ".join(
            f"{recipe_map.get(u, {}).get('title', u)[:28]}"
            f"({full_matrix.get(u, {}).get(m, 0)})"
            for u in uid_list
        )
        print(f"  {MONTH_NAMES[m]:10s}  mv={mv_val:3d}  prod={len(mp):2d}  {row}")
    print(f"\n  Unique produce covered globally: {len(all_global)}")
    print(f"  {', '.join(sorted(all_global))}")

    # Write month_selection.json for audit / debugging
    selection_out: dict = {}
    for m in range(1, 13):
        uid_list = assignments[m]
        mv_val   = _compute_mv(m, uid_list, full_matrix, dish_types)
        entries  = []
        for uid in uid_list:
            r    = recipe_map.get(uid, {})
            meta = r.get("_meta", {})
            entries.append({
                "uid":           uid,
                "title":         r.get("title", uid),
                "score":         full_matrix.get(uid, {}).get(m, 0),
                "time":          r.get("timeEstimate", ""),
                "dish_type":     dish_types.get(uid, "Other"),
                "region":        meta.get("region_tags", []),
                "holidays":      meta.get("holidays_tags", []),
                "in_season_tags": produce_for.get(uid, {}).get(m, []),
            })
        selection_out[str(m)] = {"monthly_value": mv_val, "recipes": entries}

    with open(OUT_SELECTION, "w", encoding="utf-8") as f:
        json.dump(selection_out, f, ensure_ascii=False, indent=2)
    print(f"\n  Wrote {OUT_SELECTION}")

    # ── Phase 3: Generate ─────────────────────────────────────────────────────
    print("\n-- Phase 3: Generating ---------------------------------------")
    js_content = build_js(assignments, produce_for, recipe_map, year_round_set)

    with open(OUT_SNIPPET, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"  Wrote {OUT_SNIPPET}")

    patch_index_html(INDEX_HTML, js_content)
    print(f"  Patched {INDEX_HTML}")

    # Tag summary
    print("\nTag summary:")
    for m in range(1, 13):
        print(f"{month_abbr[m]}:")
        for uid in assignments[m]:
            tags  = [t for t in produce_for.get(uid, {}).get(m, [])
                     if t not in year_round_set]
            title = recipe_map.get(uid, {}).get("title", uid)
            score = full_matrix.get(uid, {}).get(m, 0)
            src   = "opt" if produce_for.get(uid, {}).get(m) else "---"
            print(f"  [{src}] {title[:50]:50s}  {tags}")

    print("\nDone.")


if __name__ == "__main__":
    main()
