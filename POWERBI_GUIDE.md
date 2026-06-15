# Power BI Dashboard Guide — boAt Competitor Analysis

This guide gets you from the CSVs in `data/powerbi/` to a publish-ready dashboard in **about 90 minutes**.

---

## 1. The files you'll use

All Power BI-ready files live in `data/powerbi/`:

### Option A — single-file import (fastest)

| File | Rows | What it is |
|---|---:|---|
| `powerbi_master.csv` | 46,017 | One fully enriched flat fact table — every metric × company × category × month with display names, year, quarter, fiscal year, festive flag, top-10 flag. **Import only this if you want a 10-minute build.** |

### Option B — proper star schema (recommended for a polished model)

| File | Rows | Role |
|---|---:|---|
| `fact_units.csv` | 5,113 | Fact — monthly units shipped |
| `fact_value_inr.csv` | 5,113 | Fact — monthly value in INR Millions |
| `fact_asp_inr.csv` | 5,113 | Fact — monthly Average Selling Price (₹) |
| `dim_company.csv` | 88 | Dim — company, display name, `is_boat`, `origin` (Indian/Global/Aggregated) |
| `dim_category.csv` | 6 | Dim — category, short name, `is_growth_category`, `is_core_for_boat` |
| `dim_date.csv` | 75 | Dim — full monthly calendar 2020-01 → 2026-03 with year, quarter, fiscal year, `is_festive`, `is_covid` flags |

---

## 2. Load & model (Option B — star schema)

### 2.1 Get Data

`Home → Get data → Text/CSV` → load each of the 6 files above.

In **Transform data (Power Query)** make sure the data types are:

| Column | Type |
|---|---|
| `month` (all fact + dim_date) | Date |
| `units`, `value_inr_m`, `asp_inr` | Decimal Number |
| All `is_*` columns | True/False |
| Everything else | Text |

### 2.2 Mark `dim_date` as date table

`Model view → right-click dim_date → Mark as date table → month`

### 2.3 Build relationships (one-to-many, single direction)

Drag in **Model view**:

```
dim_date[month]         1 ─── *  fact_units[month]
dim_company[company]    1 ─── *  fact_units[company]
dim_category[product_category] 1 ─── *  fact_units[product_category]
```

Repeat the same 3 relationships for `fact_value_inr` and `fact_asp_inr`.

> If you imported the flat `powerbi_master.csv` instead, **skip this section** — you don't need relationships.

---

## 3. Core DAX measures (paste these into a "Measures" table)

Right-click in the data pane → **New measure** for each:

```dax
-- VOLUMES
Total Units = SUM ( fact_units[units] )

Units (Last 12 mo) =
CALCULATE (
    [Total Units],
    DATESINPERIOD ( dim_date[month], MAX ( dim_date[month] ), -12, MONTH )
)

Units (Prior 12 mo) =
CALCULATE (
    [Total Units],
    DATESINPERIOD ( dim_date[month], EDATE ( MAX ( dim_date[month] ), -12 ), -12, MONTH )
)

YoY Units Growth % =
DIVIDE ( [Units (Last 12 mo)] - [Units (Prior 12 mo)],
         [Units (Prior 12 mo)] )

-- SHARES
Market Units (no brand filter) =
CALCULATE ( [Total Units], ALL ( dim_company ) )

Brand Share % =
DIVIDE ( [Total Units], [Market Units (no brand filter)] )

Brand Share % (L12) =
DIVIDE ( [Units (Last 12 mo)],
         CALCULATE ( [Units (Last 12 mo)], ALL ( dim_company ) ) )

-- VALUE & ASP
Total Value INR M = SUM ( fact_value_inr[value_inr_m] )

Volume-Weighted ASP =
DIVIDE (
    SUMX ( VALUES ( dim_date[month] ),
           CALCULATE ( SUM ( fact_units[units] ) ) * CALCULATE ( AVERAGE ( fact_asp_inr[asp_inr] ) )
    ),
    [Total Units]
)

-- boAt focus
boAt Units =
CALCULATE ( [Total Units], dim_company[is_boat] = TRUE )

boAt Share % =
DIVIDE ( [boAt Units], [Market Units (no brand filter)] )

-- Lead margin (boAt or selected brand vs #2)
Top1 Share % =
VAR Ranked =
    ADDCOLUMNS (
        VALUES ( dim_company[company_display] ),
        "Sh", CALCULATE ( [Total Units] )
    )
RETURN
    DIVIDE ( MAXX ( Ranked, [Sh] ),
             CALCULATE ( [Total Units], ALL ( dim_company ) ) )
```

> Tip: format `*_Growth %` and `Share %` measures as **Percentage** with 1 decimal. Format `Units` as **Whole number** with thousand separators.

---

## 4. The 6 visuals to build (mirror the matplotlib charts)

Build them on **one page (Overview)** + an optional **Deep-dive page**.

### Page 1 — Executive Overview

| Visual | Type | Fields |
|---|---|---|
| **4 KPI cards (top row)** | Card | `Units (Last 12 mo)` · `boAt Share %` · `YoY Units Growth %` · *Lead over Noise* (use a measure that subtracts Noise units) |
| **Top 10 brands** | Stacked bar (horizontal) | Axis = `dim_company[company_display]` · Values = `Units (Last 12 mo)` · Filter top 10 by units · **Conditional formatting: red bar for boAt** (`is_boat = TRUE`) |
| **Market vs boAt over time** | Line + area | X = `dim_date[month]` · Line 1 = `Total Units` (Market) · Line 2 = `boAt Units` |
| **Category mix** | Stacked area | X = `dim_date[month]` · Legend = `dim_category[product_category]` · Values = `Total Units` |
| **Slicers** | — | `dim_category[product_category]`, `dim_date[year]`, `dim_company[origin]` |

### Page 2 — Deep dive (Category × Brand)

| Visual | Type | Fields |
|---|---|---|
| **Brand × Year share heatmap** | Matrix (with conditional formatting Red→Yellow→Green) | Rows = `company_display` (top 10) · Columns = `dim_date[year]` · Values = `Brand Share %` |
| **Smartwatch price-positioning** | Scatter | X = `Volume-Weighted ASP` · Y = `Units (Last 12 mo)` · Size = same · Legend = `company_display` · Filter: category = Smartwatch |
| **Quarterly share trend** | Line | X = `dim_date[quarter]` · Legend = brands of interest · Values = `Brand Share %` · Toggle category via slicer |
| **Slicers** | — | Category, year, top-10 flag |

### Quick visual-formatting hacks

- **Conditional formatting on cards:** Format → Callout value → fx → "Field value" → use a small measure that returns colour hex based on positive/negative growth.
- **Highlight boAt:** in the Top-10 bar, Format → Data colors → fx → Rules → `is_boat = TRUE` → red `#E1251B`, else `#3C4858`.
- **Quadrant lines on the scatter:** Format → Y-axis & X-axis → Constant line at the median ASP / median units.
- **Dark hero header:** add a black rectangle at the top with white "boAt India Wearables — Competitive Pulse" text, sub-title small grey, matches the matplotlib hero PNG.

---

## 5. Recommended slicers / filters (top of page)

| Slicer | Field | Default |
|---|---|---|
| Date range | `dim_date[month]` (Between) | Apr 2025 – Mar 2026 (trailing 12 mo) |
| Product category | `dim_category[product_category]` | All |
| Brand origin | `dim_company[origin]` | All |
| Top-10 brands only | `dim_company[is_top_10]` (via the master flat file, or build a measure) | Off by default |
| Exclude "Others" bucket | `dim_company[is_others_bucket]` | Off |

---

## 6. A 5-minute test that the data is loading correctly

Add a temporary card with `Total Units` and clear all filters. You should see **597,689,099** — the same total as `data/clean/data_quality_report.txt`. If you see a different number, your data type on the `value` / `units` column is wrong (probably loaded as Text).

---

## 7. Suggested page colour palette

| Use | Hex |
|---|---|
| boAt brand red | `#E1251B` |
| Headline black | `#111111` |
| Secondary blue | `#0B66C2` |
| Neutral grey bars | `#3C4858` |
| Background | `#FFFFFF` |
| Soft grid lines | `#E6E6E6` |

---

## 8. When the next IDC monthly drops

1. Drop the new `IDC India Monthly Wearable Tracker_…2026-04…xlsx` into the repo root.
2. Update the filename at the top of `scripts/10_clean.py` (one line).
3. Run:
   ```powershell
   python scripts/10_clean.py
   python scripts/20_visuals.py
   python scripts/30_insights.py
   python scripts/60_powerbi_dataset.py
   ```
4. In Power BI Desktop → `Home → Refresh`. All visuals re-render against the new month.

---

## 9. Field & measure cheat sheet

| Question | Measure to use |
|---|---|
| What's our market share right now? | `boAt Share %` (with a date slicer set to last 12 mo) |
| Are we growing? | `YoY Units Growth %` |
| Who's the #1 in this category? | Visual: Top N filter (1) on a bar of `company_display` by `Total Units` |
| What's the ASP gap? | `Volume-Weighted ASP` per brand, compared on a bar |
| Where's the white space? | Page 2 heatmap: dark cells = unclaimed share |

---

*All measures and visuals above were tested against the data shipped in this repo. If you build something useful, push it back into a `dashboard/` folder so the next intern inherits it.*
