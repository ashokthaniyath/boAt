"""
boAt Competitor Analysis — Stage 1: Clean the IDC Monthly Wearable Tracker pivot
into tidy long-form datasets ready for analysis & visualisation.

Source: 'IDC India Monthly Wearable Tracker_FinalHistoricalPivot_2026-03_Imagine Marketing (1) (1).xlsx'
Outputs (data/clean/):
    wearables_long.csv           — fully tidy: metric, product_category, company, month, value
    wearables_long.parquet       — same, compressed
    company_totals_monthly.csv   — per company, per month (Units summed across categories)
    category_totals_monthly.csv  — per product category, per month (Total rows)
    market_totals_monthly.csv    — overall market totals (Total Units / Value)
    data_quality_report.txt      — what we dropped / fixed
"""
from __future__ import annotations
from pathlib import Path
import re
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "IDC India Monthly Wearable Tracker_FinalHistoricalPivot_2026-03_Imagine Marketing (1) (1).xlsx"
OUT = ROOT / "data" / "clean"
OUT.mkdir(parents=True, exist_ok=True)

DQ: list[str] = []
def log(msg: str) -> None:
    print(msg)
    DQ.append(msg)

log("=" * 70)
log("boAt Competitor Analysis — Data Cleaning Pipeline")
log("=" * 70)

# ---------------------------------------------------------------------------
# 1) Load raw pivot, locate header row, slice data block
# ---------------------------------------------------------------------------
raw = pd.read_excel(SRC, sheet_name="Historical Data", header=None, engine="openpyxl")
log(f"\n[1] Raw pivot loaded: {raw.shape[0]} rows x {raw.shape[1]} cols")

HEADER_ROW = 42  # 0-indexed
header = raw.iloc[HEADER_ROW].tolist()
log(f"    Header row index = {HEADER_ROW}")
log(f"    Header cols 0-3 : {header[:4]}")
log(f"    First/last month columns: {header[4]} .. {header[-1]}")

# Pull data block
data = raw.iloc[HEADER_ROW + 1 :].copy()
# Drop leading empty col 0
data = data.iloc[:, 1:]
data.columns = ["metric_raw", "product_raw", "company_raw"] + [str(h) for h in header[4:]]
data.reset_index(drop=True, inplace=True)
log(f"    Data block shape: {data.shape}")

# Keep raw (pre-ffill) copies for classification, then ffill working columns
data["metric_raw_orig"] = data["metric_raw"].astype(str).str.strip().replace({"nan": np.nan, "None": np.nan})
data["product_raw_orig"] = data["product_raw"].astype(str).str.strip().replace({"nan": np.nan, "None": np.nan})

# ---------------------------------------------------------------------------
# 2) Forward-fill metric & product (pivot row labels repeat only at group start)
# ---------------------------------------------------------------------------
data["metric_raw"] = data["metric_raw"].ffill()
data["product_raw"] = data["product_raw"].ffill()

# Strip whitespace
for c in ["metric_raw", "product_raw", "company_raw"]:
    data[c] = data[c].astype(str).str.strip().replace({"nan": np.nan, "None": np.nan})

# ---------------------------------------------------------------------------
# 3) Separate the three kinds of rows
#       a) Grand-total rows           : metric_raw_orig startswith 'Total '
#       b) Product-total rows         : product_raw_orig endswith ' Total'
#       c) Company-level detail rows  : company_raw set & in a valid product category
# ---------------------------------------------------------------------------
VALID_PRODUCTS = {"Earwear", "Glasses", "Other", "Rings", "Smartwatch", "Wrist Band"}

is_grand_total = data["metric_raw_orig"].str.startswith("Total ", na=False)
is_product_total = data["product_raw_orig"].str.endswith(" Total", na=False) & ~is_grand_total
is_company_row = (
    data["company_raw"].notna()
    & data["product_raw"].isin(VALID_PRODUCTS)
    & ~is_grand_total
    & ~is_product_total
)

log(f"\n[2] Row classification:")
log(f"    company detail rows : {is_company_row.sum()}")
log(f"    product total rows  : {is_product_total.sum()}")
log(f"    grand total rows    : {is_grand_total.sum()}")
log(f"    unclassified        : {(~(is_company_row | is_product_total | is_grand_total)).sum()}")

# ---------------------------------------------------------------------------
# 4) Build TIDY long-form table for company-level data
# ---------------------------------------------------------------------------
company_block = data[is_company_row].copy()
month_cols = [c for c in data.columns if re.match(r"^\d{4}-\d{2}$", str(c))]
log(f"\n[3] Month columns detected: {len(month_cols)} "
    f"({month_cols[0]} → {month_cols[-1]})")

long = company_block.melt(
    id_vars=["metric_raw", "product_raw", "company_raw"],
    value_vars=month_cols,
    var_name="month",
    value_name="value",
)
log(f"    Melted long shape: {long.shape}")

# Drop empty cells (pivot has lots of holes where company didn't sell that month)
before = len(long)
long = long.dropna(subset=["value"])
log(f"    Dropped {before - len(long):,} empty cells "
    f"({(before-len(long))/before*100:.1f}%). Remaining: {len(long):,}")

# Coerce types
long["value"] = pd.to_numeric(long["value"], errors="coerce")
bad = long["value"].isna().sum()
if bad:
    log(f"    ! {bad} non-numeric values dropped")
    long = long.dropna(subset=["value"])

long["month"] = pd.to_datetime(long["month"], format="%Y-%m")

# Friendly metric labels
METRIC_MAP = {
    "Units":              ("units",             "Units shipped"),
    "Value (US$M)":       ("value_usd_m",       "Value (US$ Millions)"),
    "Value (INR₹M)":      ("value_inr_m",       "Value (INR Crores ≈ ₹M*10)"),
    "ASP Value (US$M)":   ("asp_value_usd_m",   "ASP-weighted value (US$M)"),
    "ASP Value (INR₹M)":  ("asp_value_inr_m",   "ASP-weighted value (₹M)"),
    "MOP (US$)":          ("mop_usd",           "Market Operating Price (US$)"),
    "MOP (INR₹)":         ("mop_inr",           "Market Operating Price (INR)"),
    "ASP (US$)":          ("asp_usd",           "Average Selling Price (US$)"),
    "ASP (INR₹)":         ("asp_inr",           "Average Selling Price (INR)"),
}
long["metric_clean"] = long["metric_raw"].str.strip()
long["metric"] = long["metric_clean"].map(lambda m: METRIC_MAP.get(m, (m.lower().replace(" ", "_"), m))[0])
long.rename(columns={"product_raw": "product_category", "company_raw": "company"}, inplace=True)
long = long[["metric", "product_category", "company", "month", "value"]].sort_values(
    ["metric", "product_category", "company", "month"]
).reset_index(drop=True)

# Tag the focal brand
BOAT_ALIASES = {"Imagine Marketing", "Imagine Marketing Pvt Ltd", "Imagine Marketing Ltd",
                "Imagine Marketing Services", "boAt"}
long["is_boat"] = long["company"].isin(BOAT_ALIASES)

log(f"\n[4] Tidy long-form preview:")
log(long.head(8).to_string())

# ---------------------------------------------------------------------------
# 5) Aggregates
# ---------------------------------------------------------------------------
# Company × month (Units only, sum across categories)
co_month_units = (
    long.query("metric == 'units'")
        .groupby(["company", "month"], as_index=False)["value"].sum()
        .rename(columns={"value": "units"})
)

# Category × month from product-total rows (Units metric)
cat_block = data[is_product_total].copy()
cat_long = cat_block.melt(id_vars=["metric_raw", "product_raw"], value_vars=month_cols,
                          var_name="month", value_name="value").dropna(subset=["value"])
cat_long["value"] = pd.to_numeric(cat_long["value"], errors="coerce")
cat_long["month"] = pd.to_datetime(cat_long["month"], format="%Y-%m")
cat_long["product_category"] = cat_long["product_raw"].str.replace(" Total", "", regex=False)
cat_long["metric"] = cat_long["metric_raw"].str.strip().map(lambda m: METRIC_MAP.get(m, (m,))[0])
cat_month = cat_long[["metric", "product_category", "month", "value"]].sort_values(
    ["metric", "product_category", "month"]
).reset_index(drop=True)

# Grand total
gt_block = data[is_grand_total].copy()
gt_long = gt_block.melt(id_vars=["metric_raw_orig"], value_vars=month_cols,
                        var_name="month", value_name="value").dropna(subset=["value"])
gt_long["value"] = pd.to_numeric(gt_long["value"], errors="coerce")
gt_long["month"] = pd.to_datetime(gt_long["month"], format="%Y-%m")
gt_long["metric"] = (gt_long["metric_raw_orig"].str.strip()
                     .str.replace(r"^Total ", "", regex=True)
                     .map(lambda m: METRIC_MAP.get(m, (m,))[0]))
market_month = gt_long[["metric", "month", "value"]].sort_values(["metric", "month"]).reset_index(drop=True)

# ---------------------------------------------------------------------------
# 6) Persist
# ---------------------------------------------------------------------------
long.to_csv(OUT / "wearables_long.csv", index=False)
try:
    long.to_parquet(OUT / "wearables_long.parquet", index=False)
    log(f"\n[5] Wrote parquet: {OUT/'wearables_long.parquet'}")
except Exception as e:
    log(f"\n[5] Parquet skipped ({e})")

co_month_units.to_csv(OUT / "company_totals_monthly.csv", index=False)
cat_month.to_csv(OUT / "category_totals_monthly.csv", index=False)
market_month.to_csv(OUT / "market_totals_monthly.csv", index=False)

# Combined Excel for the manager
with pd.ExcelWriter(OUT / "boAt_competitor_clean.xlsx", engine="openpyxl") as xw:
    long.to_excel(xw, sheet_name="tidy_long", index=False)
    co_month_units.to_excel(xw, sheet_name="company_monthly_units", index=False)
    cat_month.to_excel(xw, sheet_name="category_monthly", index=False)
    market_month.to_excel(xw, sheet_name="market_monthly", index=False)

log("\n[6] Outputs written to data/clean/")
for f in sorted(OUT.iterdir()):
    log(f"    - {f.name:42s} ({f.stat().st_size/1024:7.1f} KB)")

# Quick fact sheet
units = long.query("metric == 'units'")
log(f"\n[7] Quick facts:")
log(f"    Date range          : {units['month'].min():%Y-%m} → {units['month'].max():%Y-%m}")
log(f"    Distinct companies  : {units['company'].nunique()}")
log(f"    Distinct categories : {units['product_category'].nunique()}  ({sorted(units['product_category'].unique())})")
log(f"    Total units in file : {units['value'].sum():,.0f}")

# Write DQ report
(OUT / "data_quality_report.txt").write_text("\n".join(DQ), encoding="utf-8")
print(f"\n✔ Cleaning complete. Report: {OUT/'data_quality_report.txt'}")
