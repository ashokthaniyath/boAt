"""
Quantify competitor dominance per segment.

For each category we compute:
  - Leader share, gap to #2 (lead margin)
  - HHI (Herfindahl) — concentration index
  - Leader's share trend slope (gaining / defending / fading)
  - Leader's ASP premium vs category mean
  - How many consecutive months the leader has been #1
  - boAt's gap to leader (% points)
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
long = pd.read_csv(ROOT / "data" / "clean" / "wearables_long.csv", parse_dates=["month"])
units = long[long["metric"] == "units"]
asp   = long[long["metric"] == "asp_inr"]

BOAT = "Imagine Marketing"
END = units["month"].max()
L12 = END - pd.DateOffset(months=11)
L24 = END - pd.DateOffset(months=23)

def vw_asp(uu, pp, co=None):
    u = uu if co is None else uu[uu["company"] == co]
    p = pp if co is None else pp[pp["company"] == co]
    j = u.merge(p, on=["company", "month"], suffixes=("_u", "_p"))
    if j["value_u"].sum() == 0: return None
    return (j["value_u"] * j["value_p"]).sum() / j["value_u"].sum()

print(f"Analysis through {END:%b %Y}\n")

for cat in ["Earwear", "Smartwatch", "Smart Glasses (Glasses)", "Rings", "Wrist Band"]:
    catname = cat.split(" (")[-1].rstrip(")") if "(" in cat else cat
    u = units[units["product_category"] == catname]
    if u.empty: continue
    u12 = u[u["month"] >= L12]
    if u12["value"].sum() == 0: continue

    print("=" * 78)
    print(f"  {cat.upper()}")
    print("=" * 78)

    # Shares
    sh = u12.groupby("company")["value"].sum().sort_values(ascending=False)
    total = sh.sum()
    sh_pct = (sh / total * 100)
    leader = sh.index[0]
    runner = sh.index[1] if len(sh) > 1 else None
    lead = sh_pct.iloc[0]
    second = sh_pct.iloc[1] if len(sh_pct) > 1 else 0
    margin = lead - second

    # HHI (sum of squared share %)
    hhi = float((sh_pct ** 2).sum())

    # Months-as-leader (last 24 mo): per-month winner
    months_lead = 0
    u24 = u[u["month"] >= L24]
    by_m = u24.groupby(["month", "company"])["value"].sum().reset_index()
    for m, grp in by_m.groupby("month"):
        if grp.loc[grp["value"].idxmax(), "company"] == leader:
            months_lead += 1
    total_months = by_m["month"].nunique()

    # Leader share trend (last 12 mo slope, pp/month)
    leader_share_by_m = (u12.groupby(["month", "company"])["value"].sum().reset_index()
                        .pivot(index="month", columns="company", values="value").fillna(0))
    monthly_share = (leader_share_by_m.div(leader_share_by_m.sum(axis=1), axis=0) * 100)
    leader_series = monthly_share.get(leader, pd.Series(dtype=float))
    if len(leader_series.dropna()) >= 3:
        x = np.arange(len(leader_series))
        slope = float(np.polyfit(x, leader_series.values, 1)[0])  # pp/month
    else:
        slope = float("nan")

    # ASP comparison
    p12 = asp[(asp["product_category"] == catname) & (asp["month"] >= L12)]
    leader_asp = vw_asp(u12, p12, leader)
    cat_asp = vw_asp(u12, p12, None)
    boat_asp = vw_asp(u12, p12, BOAT)

    boat_share = sh_pct.get(BOAT, 0)
    boat_gap = lead - boat_share

    print(f"  Leader              : {leader}")
    print(f"  Leader share        : {lead:.1f}%   (#2 {runner} {second:.1f}%, margin {margin:+.1f} pp)")
    print(f"  HHI (concentration) : {hhi:,.0f}     {'fragmented' if hhi<1500 else 'moderately concentrated' if hhi<2500 else 'highly concentrated'}")
    print(f"  #1 streak           : {months_lead}/{total_months} months as leader (last 24mo)")
    print(f"  Share trend (12 mo) : {slope:+.2f} pp/month  {'GAINING' if slope > 0.1 else 'FADING' if slope < -0.1 else 'STABLE'}")
    print(f"  Leader ASP          : ₹{leader_asp:,.0f}   (cat avg ₹{cat_asp:,.0f}, premium {(leader_asp/cat_asp-1)*100:+.0f}%)" if leader_asp else "")
    print(f"  boAt share / gap    : {boat_share:.1f}%   (gap to leader: {boat_gap:+.1f} pp)")
    print(f"  boAt ASP            : {'absent' if boat_asp is None else f'₹{boat_asp:,.0f}  (vs leader ₹{leader_asp:,.0f}: {(boat_asp/leader_asp - 1)*100:+.0f}%)'}")
    # Top 5
    print(f"  Top-5 share         :", "  ".join(f"{c}:{sh_pct[c]:.1f}%" for c in sh_pct.head(5).index))
    print()
