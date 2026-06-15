"""
boAt Competitor Analysis — Stage 3: Generate quantitative insights JSON
that the README pulls from, so all numbers in the report stay in sync with data.
"""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "data" / "clean"

long = pd.read_csv(OUT / "wearables_long.csv", parse_dates=["month"])
units = long[long["metric"] == "units"].copy()
asp_inr = long[long["metric"] == "asp_inr"].copy()
val_inr = long[long["metric"] == "value_inr_m"].copy()  # value in INR Millions

DATA_END = units["month"].max()
LAST12 = units["month"].max() - pd.DateOffset(months=11)
PRIOR_END = LAST12 - pd.DateOffset(months=1)
PRIOR_START = PRIOR_END - pd.DateOffset(months=11)

def share_table(sub_units: pd.DataFrame, by="company"):
    g = sub_units.groupby(by)["value"].sum().sort_values(ascending=False)
    return (g / g.sum() * 100).round(2), g.round(0)

facts = {}
facts["data_end"] = DATA_END.strftime("%Y-%m")
facts["analysis_window"] = f"{LAST12:%b %Y} \u2013 {DATA_END:%b %Y}"

# --- overall ---
l12 = units[units["month"] >= LAST12]
prior = units[(units["month"] >= PRIOR_START) & (units["month"] <= PRIOR_END)]
total_units_l12 = l12["value"].sum()
total_units_prior = prior["value"].sum()
facts["market"] = {
    "total_units_last12mo": int(total_units_l12),
    "total_units_prior12mo": int(total_units_prior),
    "yoy_growth_pct": round((total_units_l12 / total_units_prior - 1) * 100, 2),
}

shares, vols = share_table(l12)
facts["top10_overall"] = [
    {"company": c, "units": int(v), "share_pct": float(shares[c])}
    for c, v in vols.head(10).items()
]

boat = "Imagine Marketing"
facts["boat"] = {
    "units_last12mo": int(vols.get(boat, 0)),
    "share_pct": float(shares.get(boat, 0)),
    "yoy_units_pct": round(
        (l12.query(f"company == @boat")['value'].sum()
         / prior.query(f"company == @boat")['value'].sum() - 1) * 100, 2),
    "rank": int(vols.index.get_loc(boat) + 1) if boat in vols.index else None,
}

# --- by category ---
cats = {}
for cat in sorted(units["product_category"].unique()):
    sub = l12[l12["product_category"] == cat]
    if sub["value"].sum() == 0:
        continue
    sh, vo = share_table(sub)
    sub_prior = prior[prior["product_category"] == cat]
    sh_p, vo_p = share_table(sub_prior) if sub_prior["value"].sum() > 0 else (pd.Series(dtype=float), pd.Series(dtype=float))
    top5 = []
    for c in vo.head(5).index:
        delta = float(sh[c]) - float(sh_p.get(c, 0))
        top5.append({"company": c, "share_pct": float(sh[c]),
                     "share_pct_prior": float(sh_p.get(c, 0)),
                     "share_pp_change": round(delta, 2)})
    boat_share = float(sh.get(boat, 0))
    boat_rank = int(vo.index.get_loc(boat) + 1) if boat in vo.index else None
    cats[cat] = {
        "total_units_l12": int(sub["value"].sum()),
        "total_units_prior": int(sub_prior["value"].sum()),
        "yoy_pct": round((sub["value"].sum() / sub_prior["value"].sum() - 1) * 100, 2)
                   if sub_prior["value"].sum() else None,
        "top5": top5,
        "boat_share_pct": boat_share,
        "boat_rank": boat_rank,
    }
facts["categories"] = cats

# --- price positioning: smartwatch volume-weighted ASP ---
sw_u = units[(units["product_category"] == "Smartwatch") & (units["month"] >= LAST12)]
sw_p = asp_inr[(asp_inr["product_category"] == "Smartwatch") & (asp_inr["month"] >= LAST12)]
j = sw_u.merge(sw_p, on=["company", "month"], suffixes=("_u", "_p"))
j["spend"] = j["value_u"] * j["value_p"]
asp_tbl = (j.groupby("company").agg(units=("value_u", "sum"), spend=("spend", "sum"))
            .assign(asp=lambda d: d["spend"] / d["units"])
            .sort_values("units", ascending=False)
            .head(8))
facts["smartwatch_asp"] = [
    {"company": c, "units": int(r["units"]), "asp_inr": round(float(r["asp"]), 0)}
    for c, r in asp_tbl.iterrows()
]

# --- recent 3-month momentum (Q1 2026 mar) ---
last3 = units[units["month"] >= (DATA_END - pd.DateOffset(months=2))]
sh3, vo3 = share_table(last3)
facts["last3mo_top5"] = [
    {"company": c, "units": int(vo3[c]), "share_pct": float(sh3[c])}
    for c in vo3.head(5).index
]

(OUT / "insights.json").write_text(json.dumps(facts, indent=2), encoding="utf-8")
print(json.dumps(facts, indent=2))
print(f"\n\u2714 Wrote {OUT/'insights.json'}")
