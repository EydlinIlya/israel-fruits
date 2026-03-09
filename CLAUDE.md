# CLAUDE.md — Israel Seasonal Produce Calendar

## Project overview

Single-file static web app (`index.html`). No build system, no npm, no frameworks. Everything — HTML, CSS, JavaScript, and data — lives in one file.

## Architecture

All logic is in `index.html`:

- **CSS** (~730 lines) — custom properties (CSS variables), no external CSS framework
- **HTML** — semantic structure; chart built entirely by JS at runtime
- **JS** — vanilla JS, no libraries

### Key JS globals

| Name | Type | Purpose |
|------|------|---------|
| `RAW` | object | All produce data: `RAW.fruits`, `RAW.vegetables`, `RAW.herbs` |
| `MONTH_DISHES` | object | Dish suggestions keyed by month number (1–12) |
| `filterCat` | string | Active category filter: `'all'` \| `'fruit'` \| `'veg'` \| `'herb'` |
| `filterMonth` | number\|null | Active month filter (1–12) or `null` |
| `searchQ` | string | Lowercase search string |
| `sortMode` | string | `'name'` \| `'months-desc'` \| `'months-asc'` |

### Key functions

| Function | What it does |
|----------|-------------|
| `buildHead()` | Renders the two-row Gantt thead (season row + month row) |
| `buildBody()` | Renders category headers + produce rows, applies all filters |
| `buildDishPanel()` | Renders the dish suggestions panel (uses `filterMonth ?? NOW_MONTH`) |
| `buildMobilePanel()` | Renders the mobile current-month produce grid (always `NOW_MONTH`) |
| `setFilter(f)` | Sets category filter, rebuilds body |
| `setMonthFilter(m)` | Toggles month filter, rebuilds head + body + dish panel |
| `setSearch(q)` | Sets search query, rebuilds body |
| `setSort(v)` | Sets sort mode, rebuilds body |

## Design system

All colours are CSS custom properties defined in `:root`. Palette:

- `--bg` / `--surface` / `--surface-2` — warm parchment backgrounds
- `--green-*` — brand greens (produce, in-season bars)
- `--terra-*` — terracotta (fruit bars)
- `--sage-*` — sage green (herb bars)
- `--gold-*` — harvest gold (accents)
- `--ink-*` — text colours (dark to faint)
- `--s-winter-*` / `--s-spring-*` / `--s-summer-*` / `--s-autumn-*` — season colours

Fonts: `Playfair Display` (headings, labels) + `DM Sans` (body) — loaded from Google Fonts.

## Responsive breakpoints

- `≤ 768px` — mobile: Gantt hidden, dish carousel shown, mobile produce grid shown
- `≤ 640px` — small mobile: header padding adjustments, deco SVGs hidden

## Data format

Each produce item:
```js
{ name: "Strawberries", emoji: "🍓", months: [1,2,3,4,5,6,11,12] }
```
`months` is an array of integers 1–12 (January = 1).

Each dish entry in `MONTH_DISHES`:
```js
{ name: "Dish Name", time: "20 min", cuisine: "Israeli", desc: "...", tags: ["🍓 Strawberries", "🌿 Mint"] }
```

## Common tasks

**Add a new produce item:**
Find the correct array in `RAW` (fruits/vegetables/herbs) and add a new object with `name`, `emoji`, and `months`.

**Update a seasonal window:**
Adjust the `months` array of the relevant item in `RAW`.

**Add/change a dish suggestion:**
Edit the relevant month's array in `MONTH_DISHES`.

**Add a new season colour:**
Add CSS custom properties to `:root` and apply them in the relevant `.th-season` / `.season-chip` rules.

## Important notes

- The Gantt uses `border-collapse: collapse`. Season header cells (`.th-season`) and month header cells (`.th-month`) **must both have** `border-left: 1px solid rgba(255,255,255,0.15)` to stay pixel-aligned.
- `buildHead()` must be called whenever `filterMonth` changes (to update `.month-active` class).
- `buildMobilePanel()` always uses `NOW_MONTH` — it ignores `filterMonth`.
