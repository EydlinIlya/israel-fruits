# 🌿 Israel's Seasonal Produce Calendar

**Live site → [eydlinilya.github.io/israel-fruits](https://eydlinilya.github.io/israel-fruits/)**

An interactive, beautifully designed month-by-month harvest guide to the freshest fruits, vegetables and herbs of Israel — with curated Middle Eastern & Jewish cuisine dish suggestions for each month.

## Features

- **Gantt-style calendar** — visualize seasonal availability across all 12 months at a glance
- **Month filter** — click any month header to filter to just that month's in-season produce; click again to clear
- **Dish suggestions** — 2–3 recipes per month using current seasonal ingredients, with a focus on Middle Eastern and Jewish cuisine (Levantine, Moroccan-Jewish, Ashkenazi, Sephardic, Israeli-modern)
- **Category filter** — toggle between Fruits, Vegetables and Herbs
- **Live search** — instantly filter produce by name
- **Sort options** — alphabetical, most months, fewest months
- **Mobile layout** — no chart clutter on small screens; instead shows a clean in-season produce grid and a swipeable dish-card carousel
- **Current month highlighting** — today's month is always visually marked
- **Year-round badge** — items available all year are tagged `YR`

## Data

Seasonal availability data is sourced from [Anglo-List — Israel's Seasonal Fruits & Vegetables](https://anglo-list.com/israels-seasonal-fruits-vegetables/) (last updated December 2021).

Covers **40+ fruits**, **31 vegetables** and **10 herbs**.

## Usage

This is a single-file static app — no build step, no dependencies, no server required.

```bash
# Clone
git clone https://github.com/EydlinIlya/israel-fruits.git
cd israel-fruits

# Open
open index.html   # macOS
start index.html  # Windows
xdg-open index.html  # Linux
```

Or just download `index.html` and open it in any modern browser.

## Structure

```
index.html          — everything: HTML, CSS, JS and data in one self-contained file
seasonal_produce.json  — raw data (also embedded inside index.html)
preview*.png        — screenshots
```

## Seasons (Israel)

| Season | Months |
|--------|--------|
| ❄ Winter | December · January · February |
| 🌸 Spring | March · April · May |
| ☀ Summer | June · July · August |
| 🍂 Autumn | September · October · November |

## Contributing

Pull requests welcome. Common improvements:

- Correcting or updating seasonal availability data
- Adding missing produce varieties
- Adding or refining dish suggestions
- Translations (Hebrew, Arabic, Russian)
- Accessibility improvements

## License

MIT — see [LICENSE](LICENSE).
