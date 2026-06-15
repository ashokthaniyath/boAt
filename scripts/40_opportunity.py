"""
Where should boAt play harder, and which products need a refresh?

Opportunity score per (segment) = combination of:
    - Category 12-mo growth (size of the wave)
    - boAt's current share (do we already have permission to play?)
    - boAt's 3-mo momentum vs prior 3 mo (are we already moving?)
    - Price-headroom: gap between boAt ASP and the category-leader ASP (₹)

Also flags products that need improvement = segments where boAt:
    - lost share YoY, OR
    - has noticeably lower ASP than the leader (premium feature gap), OR
    - is absent in a fast-growing segment.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
long = pd.read_csv(ROOT / "data" / "clean" / "wearables_long.csv", parse_dates=["month"])

BOAT = "Imagine Marketing"
DATA_END = long["month"].max()
L12 = DATA_END - pd.DateOffset(months=11)
PRIOR_END = L12 - pd.DateOffset(months=1)
PRIOR_START = PRIOR_END - pd.DateOffset(months=11)
LAST3 = DATA_END - pd.DateOffset(months=2)
PRIOR3_END = LAST3 - pd.DateOffset(months=1)
PRIOR3_START = PRIOR3_END - pd.DateOffset(months=2)

units   = long[long["metric"] == "units"]
asp_inr = long[long["metric"] == "asp_inr"]

def vol_weighted_asp(df_u: pd.DataFrame, df_p: pd.DataFrame, company: str) -> float | None:
    u = df_u[df_u["company"] == company]
    p = df_p[df_p["company"] == company]
    j = u.merge(p, on=["company", "month", "product_category"], suffixes=("_u", "_p"))
    if j["value_u"].sum() == 0:
        return None
    return (j["value_u"] * j["value_p"]).sum() / j["value_u"].sum()

print(f"Analysis through {DATA_END:%b %Y}\n")
print("=" * 96)
print(f"{'Category':<12} {'MktGrwYoY':>10} {'boAtShare':>10} {'boAtRank':>8} "
      f"{'boAtYoY%':>9} {'boAt3mo':>9} {'boAtASP₹':>10} {'LeaderASP₹':>11} {'Gap':>8}")
print("-" * 96)

rows = []
for cat in sorted(units["product_category"].unique()):
    u_l12 = units[(units["product_category"] == cat) & (units["month"] >= L12)]
    u_pri = units[(units["product_category"] == cat)
                  & (units["month"] >= PRIOR_START) & (units["month"] <= PRIOR_END)]
    tot_l12  = u_l12["value"].sum()
    tot_pri  = u_pri["value"].sum()
    if tot_l12 == 0:
        continue
    mkt_yoy = (tot_l12 / tot_pri - 1) * 100 if tot_pri else float("inf")

    by_co = u_l12.groupby("company")["value"].sum().sort_values(ascending=False)
    boat_u = by_co.get(BOAT, 0)
    boat_share = boat_u / tot_l12 * 100
    boat_rank = by_co.index.get_loc(BOAT) + 1 if BOAT in by_co.index else None

    boat_pri = u_pri[u_pri["company"] == BOAT]["value"].sum()
    boat_yoy = (boat_u / boat_pri - 1) * 100 if boat_pri else None

    u_l3   = units[(units["product_category"] == cat) & (units["month"] >= LAST3)]
    u_p3   = units[(units["product_category"] == cat)
                   & (units["month"] >= PRIOR3_START) & (units["month"] <= PRIOR3_END)]
    boat_l3 = u_l3[u_l3["company"] == BOAT]["value"].sum()
    boat_p3 = u_p3[u_p3["company"] == BOAT]["value"].sum()
    boat_mom = (boat_l3 / boat_p3 - 1) * 100 if boat_p3 else None

    p_l12 = asp_inr[(asp_inr["product_category"] == cat) & (asp_inr["month"] >= L12)]
    boat_asp = vol_weighted_asp(u_l12, p_l12, BOAT)
    leader   = by_co.index[0]
    leader_asp = vol_weighted_asp(u_l12, p_l12, leader)
    gap = (leader_asp - boat_asp) if (boat_asp and leader_asp) else None

    rows.append(dict(category=cat, mkt_l12=tot_l12, mkt_yoy=mkt_yoy,
                     boat_share=boat_share, boat_rank=boat_rank,
                     boat_yoy=boat_yoy, boat_mom=boat_mom,
                     boat_asp=boat_asp, leader=leader, leader_asp=leader_asp, gap=gap))

    def f(x, fmt):
        return ("--" if x is None else fmt.format(x))
    print(f"{cat:<12} {mkt_yoy:>9.1f}% {boat_share:>9.1f}% {f(boat_rank,'{:>8d}')} "
          f"{f(boat_yoy,'{:>8.1f}%')} {f(boat_mom,'{:>8.1f}%')} "
          f"{f(boat_asp,'{:>10,.0f}')} {f(leader_asp,'{:>11,.0f}')} {f(gap,'{:>+8,.0f}')}")

print()
print("Leader by category (last 12 mo, units):")
for r in rows:
    print(f"  {r['category']:<12}  leader = {r['leader']}")

print("\n" + "=" * 96)
print("OPPORTUNITY SCORE (1-10 scale; higher = bigger 'where to grow' bet)")
print("=" * 96)

# Simple opportunity score: emphasise market growth + headroom (1 - share/40)
# plus a momentum bonus and a price-headroom bonus
import math
def clip(x, lo, hi): return max(lo, min(hi, x))

scored = []
for r in rows:
    g  = clip(r["mkt_yoy"] / 30, -2, 5) if r["mkt_yoy"] is not None else 0       # growth weight, capped
    h  = clip((40 - r["boat_share"]) / 8, 0, 5)                                   # headroom weight
    m  = clip((r["boat_mom"] or 0) / 20, -2, 3)                                   # momentum weight
    p  = clip(((r["gap"] or 0) / 1000), 0, 2)                                     # price headroom weight
    score = max(0, min(10, g + h + m + p + 3))                                    # baseline 3
    scored.append((score, r))

for score, r in sorted(scored, key=lambda x: -x[0]):
    print(f"  {r['category']:<12}  score = {score:>4.1f}   "
          f"(growth {r['mkt_yoy']:+.0f}%, share {r['boat_share']:.0f}%, "
          f"3-mo mom {('--' if r['boat_mom'] is None else f'{r['boat_mom']:+.0f}%')}, "
          f"price gap ₹{('--' if r['gap'] is None else f'{r['gap']:+,.0f}')})")

# ---- Product / SKU improvement flags ----------------------------------
print("\n" + "=" * 96)
print("PRODUCT IMPROVEMENT FLAGS")
print("=" * 96)

flags = []
for r in rows:
    f = []
    if r["boat_yoy"] is not None and r["boat_yoy"] < -2:
        f.append(f"LOSING UNITS — boAt {r['boat_yoy']:+.1f}% YoY in a market that did {r['mkt_yoy']:+.1f}%")
    if r["gap"] is not None and r["gap"] > 200:
        f.append(f"PREMIUM GAP — leader ({r['leader']}) ASP ₹{r['leader_asp']:.0f}, "
                 f"boAt ASP ₹{r['boat_asp']:.0f} → headroom ₹{r['gap']:+.0f}")
    if r["boat_share"] < 5 and r["mkt_yoy"] > 30:
        f.append(f"ABSENT IN A WAVE — category up {r['mkt_yoy']:+.0f}% but boAt only {r['boat_share']:.1f}% share")
    if r["boat_mom"] is not None and r["boat_yoy"] is not None and r["boat_mom"] < r["boat_yoy"] - 5:
        f.append(f"MOMENTUM DROP — 3-mo run-rate ({r['boat_mom']:+.0f}%) trailing trailing-12 ({r['boat_yoy']:+.0f}%)")
    if r["boat_share"] > 20 and (r["boat_yoy"] or 0) < 0:
        f.append("INCUMBENT EROSION — we are share-leader but lost units YoY")
    if f:
        flags.append((r["category"], f))

for cat, fs in flags:
    print(f"\n  ▶ {cat}")
    for x in fs:
        print(f"      - {x}")

# ---- Smartwatch price-band analysis (where competitors monetise) ----
print("\n" + "=" * 96)
print("SMARTWATCH PRICE LADDER — who owns each tier (last 12 mo)")
print("=" * 96)
sw_u = units[(units["product_category"] == "Smartwatch") & (units["month"] >= L12)]
sw_p = asp_inr[(asp_inr["product_category"] == "Smartwatch") & (asp_inr["month"] >= L12)]
asp_tbl = []
for co in sw_u["company"].unique():
    j = sw_u[sw_u["company"] == co].merge(sw_p[sw_p["company"] == co], on=["company", "month"], suffixes=("_u","_p"))
    if j["value_u"].sum() < 50000:
        continue
    asp = (j["value_u"]*j["value_p"]).sum() / j["value_u"].sum()
    asp_tbl.append((co, j["value_u"].sum(), asp))
asp_tbl.sort(key=lambda x: x[2])
print(f"  {'Brand':<25} {'ASP₹':>9} {'Units(12mo)':>14}  {'Tier':<14}")
for co, u, asp in asp_tbl:
    if asp < 1100:  tier = "Sub-1.1k value"
    elif asp < 1500: tier = "Mass 1.1-1.5k"
    elif asp < 1800: tier = "Mid 1.5-1.8k"
    elif asp < 2500: tier = "Premium 1.8-2.5k"
    else:            tier = "Lux 2.5k+"
    star = "  ← boAt" if co == BOAT else ""
    print(f"  {co:<25} {asp:>9,.0f} {u:>14,.0f}  {tier:<14}{star}")
