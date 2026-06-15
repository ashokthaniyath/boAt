"""
Build Power BI-ready datasets from the cleaned long-form data.

Outputs in data/powerbi/:
    powerbi_master.csv     — single enriched flat fact table (easiest to import)
    fact_units.csv         — star-schema fact: units only
    fact_value_inr.csv     — star-schema fact: value in INR millions
    fact_asp_inr.csv       — star-schema fact: ASP in INR
    dim_company.csv        — company dimension with display name + is_boat flag
    dim_category.csv       — product category dimension
    dim_date.csv           — date dimension (monthly grain, 2020-01 ... 2026-03)
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "data" / "powerbi"
OUT.mkdir(parents=True, exist_ok=True)

long = pd.read_csv(ROOT / "data" / "clean" / "wearables_long.csv", parse_dates=["month"])
print(f"Loaded {len(long):,} rows from clean dataset")

# -- Display labels (same mapping used in the charts) ------------------------
DISPLAY = {
    "Imagine Marketing":      "boAt",
    "Nexxbase":               "Noise",
    "GoBoult":                "Boult",
    "Fire - Boltt":           "Fire-Boltt",
    "SRK Powertech":          "SRK Powertech",
    "Eccentric Enterprises":  "Eccentric",
    "Number Fone Company":    "Number Fone",
    "Dizo Innovation Pvt. Ltd": "Dizo",
}
METRIC_LABEL = {
    "units":           "Units shipped",
    "value_usd_m":     "Value (US$ M)",
    "value_inr_m":     "Value (INR Million)",
    "asp_value_usd_m": "ASP-weighted Value (US$ M)",
    "asp_value_inr_m": "ASP-weighted Value (INR M)",
    "mop_usd":         "MOP (US$)",
    "mop_inr":         "MOP (INR)",
    "asp_usd":         "ASP (US$)",
    "asp_inr":         "ASP (INR)",
}

# =====================================================================
# 1) Flat enriched master table — easiest single-import for Power BI
# =====================================================================
master = long.copy()
master["company_display"] = master["company"].map(DISPLAY).fillna(master["company"])
master["metric_label"] = master["metric"].map(METRIC_LABEL).fillna(master["metric"])
master["year"]    = master["month"].dt.year
master["quarter"] = master["month"].dt.to_period("Q").astype(str)         # 2024Q1
master["year_month"] = master["month"].dt.strftime("%Y-%m")
master["month_name"] = master["month"].dt.strftime("%b %Y")
master["fiscal_year"] = master["month"].apply(
    lambda d: f"FY{d.year + 1 - 2000:02d}" if d.month >= 4 else f"FY{d.year - 2000:02d}"
)
# Helpful boolean for filters
master["is_top10_brand"] = master["company"].isin([
    "Imagine Marketing", "Nexxbase", "GoBoult", "Fire - Boltt", "OPPO",
    "Samsung", "Titan", "Apple", "Nothing", "Mivi"
])
master = master[[
    "month", "year_month", "month_name", "year", "quarter", "fiscal_year",
    "metric", "metric_label",
    "product_category",
    "company", "company_display", "is_boat", "is_top10_brand",
    "value",
]].sort_values(["metric", "month", "product_category", "company"])

master.to_csv(OUT / "powerbi_master.csv", index=False)
print(f"  ✓ powerbi_master.csv  ({len(master):,} rows)")

# =====================================================================
# 2) Star schema — for users who want a proper model
# =====================================================================
# --- dim_company ---
co = (long.groupby("company")["value"].count().rename("rows_in_data")
        .reset_index()
        .rename(columns={"company": "company"}))
co["company_display"] = co["company"].map(DISPLAY).fillna(co["company"])
co["is_boat"] = co["company"] == "Imagine Marketing"
co["is_others_bucket"] = co["company"] == "Others"
# Country-of-origin heuristic for slicers (best-effort)
INDIAN_BRANDS = {
    "Imagine Marketing", "Nexxbase", "GoBoult", "Fire - Boltt", "Titan", "Mivi",
    "Portronics", "Zebronics", "Ubon", "BeatXP", "Gizmore", "Crossbeats",
    "Eccentric Enterprises", "Brandscale", "Ambrane", "SRK Powertech",
    "Lenskart", "Riot Labz", "Number Fone Company", "Dynamic Conglomerate",
    "Palred", "Dizo Innovation Pvt. Ltd", "Nothing", "Ultrahuman", "Gabit",
    "Aabo", "Fittr", "Muse",
}
co["origin"] = co["company"].apply(lambda c: "Indian" if c in INDIAN_BRANDS else
                                    ("Aggregated" if c == "Others" else "Global"))
co.to_csv(OUT / "dim_company.csv", index=False)
print(f"  ✓ dim_company.csv     ({len(co):,} companies)")

# --- dim_category ---
cat = pd.DataFrame({"product_category": sorted(long["product_category"].unique())})
cat["category_short"] = cat["product_category"].replace({
    "Wrist Band": "Bands", "Smartwatch": "Watches", "Earwear": "TWS",
    "Glasses": "Glasses", "Rings": "Rings", "Other": "Other"
})
cat["is_growth_category"] = cat["product_category"].isin(["Glasses", "Rings"])
cat["is_core_for_boat"]   = cat["product_category"].isin(["Earwear", "Smartwatch", "Rings"])
cat.to_csv(OUT / "dim_category.csv", index=False)
print(f"  ✓ dim_category.csv    ({len(cat):,} categories)")

# --- dim_date (monthly grain, full coverage) ---
date_range = pd.date_range(long["month"].min(), long["month"].max(), freq="MS")
dim_date = pd.DataFrame({"month": date_range})
dim_date["year"]        = dim_date["month"].dt.year
dim_date["quarter"]     = dim_date["month"].dt.to_period("Q").astype(str)
dim_date["quarter_num"] = dim_date["month"].dt.quarter
dim_date["month_num"]   = dim_date["month"].dt.month
dim_date["year_month"]  = dim_date["month"].dt.strftime("%Y-%m")
dim_date["month_name"]  = dim_date["month"].dt.strftime("%b %Y")
dim_date["fiscal_year"] = dim_date["month"].apply(
    lambda d: f"FY{d.year + 1 - 2000:02d}" if d.month >= 4 else f"FY{d.year - 2000:02d}"
)
dim_date["is_festive"]  = dim_date["month_num"].isin([9, 10, 11])  # Onam/Dussehra/Diwali window
dim_date["is_covid"]    = (dim_date["month"] >= "2020-03") & (dim_date["month"] <= "2021-06")
dim_date.to_csv(OUT / "dim_date.csv", index=False)
print(f"  ✓ dim_date.csv        ({len(dim_date):,} months)")

# --- fact tables: one per metric (keeps the model tight) ---
def write_fact(metric: str, fname: str) -> None:
    f = long[long["metric"] == metric][["month", "product_category", "company", "value"]].copy()
    f.rename(columns={"value": metric}, inplace=True)
    f.to_csv(OUT / fname, index=False)
    print(f"  ✓ {fname:<22} ({len(f):,} rows)")

write_fact("units",        "fact_units.csv")
write_fact("value_inr_m",  "fact_value_inr.csv")
write_fact("asp_inr",      "fact_asp_inr.csv")

# =====================================================================
# 3) Quick sanity check — totals match clean dataset
# =====================================================================
print("\nSanity checks:")
print(f"  master rows               = {len(master):,}")
print(f"  flat-file unit total      = {master.query('metric == \"units\"')['value'].sum():,.0f}")
fact_u = pd.read_csv(OUT / "fact_units.csv")
print(f"  fact_units.csv unit total = {fact_u['units'].sum():,.0f}")
print(f"  companies                 = {co['company'].nunique()}  (incl. 'Others')")
print(f"  date range                = {dim_date['month'].min():%Y-%m} → {dim_date['month'].max():%Y-%m}")

print(f"\n✔ Power BI dataset written to {OUT}")
