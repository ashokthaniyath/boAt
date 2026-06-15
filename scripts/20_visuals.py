"""
boAt Competitor Analysis — Stage 2: Generate the visual deck.

Charts produced in charts/:
    01_hero_dashboard.png            — single-frame executive snapshot
    02_top10_last12mo.png            — overall top-10 brands bar
    03_earwear_share_trend.png       — quarterly Earwear share, boAt vs peers
    04_smartwatch_share_trend.png    — quarterly Smartwatch share (boAt is losing)
    05_category_mix_area.png         — market category mix evolution
    06_market_size_monthly.png       — total India wearables units / month
    07_boat_growth.png               — boAt monthly units trajectory + annotations
    08_share_heatmap.png             — brand × year heatmap of share
    09_price_positioning.png         — ASP vs Volume scatter (positioning map)
    10_kid_simple_share_pie.png      — simple "who sold the most" pie

Design: white background, boAt-red accent (#E1251B), heavy titles, callouts
with the "so what" so a 12-yr-old gets it AND an MBA respects it.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "charts"
OUT.mkdir(exist_ok=True)

# -- Brand styling --------------------------------------------------------
BOAT_RED    = "#E1251B"
BOAT_BLACK  = "#111111"
INK         = "#1f1f1f"
SOFT_GREY   = "#E6E6E6"
ACCENT_BLUE = "#0B66C2"
PALETTE = ["#E1251B", "#0B66C2", "#7A3FB8", "#11A578", "#F39C12",
           "#34495E", "#16A085", "#C0392B", "#8E44AD", "#2C3E50"]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 16,
    "axes.titleweight": "bold",
    "axes.labelsize": 12,
    "axes.edgecolor": "#888888",
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.labelcolor": INK,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.dpi": 160,
    "figure.dpi": 110,
})

def thousands(x, _): return f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"
def percent(x, _):   return f"{x:.0f}%"
def crore(x, _):     return f"₹{x/1e3:.1f}K Cr"  # value INR M -> Cr (=10 INR M)

# Brand → display label
DISPLAY = {
    "Imagine Marketing": "boAt",
    "Nexxbase":          "Noise",
    "GoBoult":           "Boult",
    "Fire - Boltt":      "Fire-Boltt",
    "SRK Powertech":     "SRK Powertech",
    "Eccentric Enterprises": "Eccentric",
    "Number Fone Company":   "Number Fone",
}
def label(c): return DISPLAY.get(c, c)

# -- Load clean data ------------------------------------------------------
long = pd.read_csv(ROOT / "data" / "clean" / "wearables_long.csv", parse_dates=["month"])
cat_month = pd.read_csv(ROOT / "data" / "clean" / "category_totals_monthly.csv", parse_dates=["month"])
market_month = pd.read_csv(ROOT / "data" / "clean" / "market_totals_monthly.csv", parse_dates=["month"])

units = long[long["metric"] == "units"].copy()
asp_inr = long[long["metric"] == "asp_inr"].copy()
val_inr = long[long["metric"] == "value_inr_m"].copy()

DATA_END = units["month"].max()
LAST12_START = DATA_END - pd.DateOffset(months=11)
print(f"Data through {DATA_END:%b %Y}")
print(f"Charts dir: {OUT}")

# ----------------------------------------------------------------------------
# Chart 1 — HERO DASHBOARD (single image, 4 KPI tiles + 2 charts)
# ----------------------------------------------------------------------------
def hero():
    last12_units = units[units["month"] >= LAST12_START]
    market_units_12 = last12_units["value"].sum()
    boat_units_12 = last12_units.query("company == 'Imagine Marketing'")["value"].sum()
    boat_share = boat_units_12 / market_units_12 * 100
    noise_units_12 = last12_units.query("company == 'Nexxbase'")["value"].sum()

    # YoY: last 12 vs prior 12
    prior_start = LAST12_START - pd.DateOffset(months=12)
    prior_end   = LAST12_START - pd.DateOffset(months=1)
    prior_units = units[(units["month"] >= prior_start) & (units["month"] <= prior_end)]
    boat_units_prior = prior_units.query("company == 'Imagine Marketing'")["value"].sum()
    boat_yoy = (boat_units_12 / boat_units_prior - 1) * 100 if boat_units_prior else 0
    mkt_yoy = (market_units_12 / prior_units["value"].sum() - 1) * 100

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 4, height_ratios=[0.55, 1, 1], hspace=0.55, wspace=0.35,
                          left=0.05, right=0.97, top=0.93, bottom=0.07)

    # Title banner
    fig.suptitle("boAt India Wearables — Competitive Pulse",
                 fontsize=26, fontweight="bold", color=BOAT_BLACK, x=0.06, ha="left", y=0.985)
    fig.text(0.06, 0.945,
             f"Source: IDC India Monthly Wearable Tracker · last 12 months ending {DATA_END:%b %Y}",
             fontsize=11, color="#555555")

    # KPI tiles
    def kpi(ax, title, value, sub, color=BOAT_RED):
        ax.axis("off")
        box = FancyBboxPatch((0.02, 0.1), 0.96, 0.8, boxstyle="round,pad=0.02,rounding_size=0.04",
                             linewidth=0, facecolor="#F7F7F9", transform=ax.transAxes)
        ax.add_patch(box)
        ax.text(0.5, 0.78, title, ha="center", va="top", fontsize=11,
                color="#666", transform=ax.transAxes, fontweight="bold")
        ax.text(0.5, 0.50, value, ha="center", va="center", fontsize=30,
                color=color, fontweight="bold", transform=ax.transAxes)
        ax.text(0.5, 0.18, sub, ha="center", va="center", fontsize=10,
                color="#444", transform=ax.transAxes)

    kpi(fig.add_subplot(gs[0, 0]), "boAt Units (12 mo)",
        f"{boat_units_12/1e6:.1f}M", "wearables shipped")
    kpi(fig.add_subplot(gs[0, 1]), "Market Share (overall)",
        f"{boat_share:.1f}%", "#1 brand in India")
    kpi(fig.add_subplot(gs[0, 2]), "boAt YoY Growth",
        f"{boat_yoy:+.1f}%", f"market grew {mkt_yoy:+.1f}%",
        color=ACCENT_BLUE if boat_yoy >= 0 else BOAT_RED)
    kpi(fig.add_subplot(gs[0, 3]), "Lead over #2 (Noise)",
        f"{(boat_units_12-noise_units_12)/1e6:.1f}M units",
        f"≈ {boat_units_12/noise_units_12:.1f}× their volume")

    # Bottom-left: top-8 brands bar
    ax1 = fig.add_subplot(gs[1:, :2])
    top = last12_units.groupby("company")["value"].sum().sort_values(ascending=False).head(8)
    names = [label(c) for c in top.index]
    colors = [BOAT_RED if c == "Imagine Marketing" else "#B0B6BE" for c in top.index]
    bars = ax1.barh(names[::-1], (top.values/1e6)[::-1], color=colors[::-1], edgecolor="white")
    ax1.set_title("Who shipped the most wearables? (last 12 months)", loc="left", color=BOAT_BLACK)
    ax1.set_xlabel("Units shipped (millions)")
    for b, v in zip(bars, (top.values/1e6)[::-1]):
        ax1.text(v + 0.4, b.get_y() + b.get_height()/2, f"{v:.1f}M",
                 va="center", fontsize=10, color=INK, fontweight="bold")
    ax1.set_xlim(0, top.values.max()/1e6 * 1.18)
    ax1.grid(axis="x", linestyle=":", alpha=0.4)

    # Bottom-right: market trend area + boAt line
    ax2 = fig.add_subplot(gs[1:, 2:])
    mkt = units.groupby("month")["value"].sum().sort_index()
    boat_m = units.query("company == 'Imagine Marketing'").groupby("month")["value"].sum().sort_index()
    ax2.fill_between(mkt.index, mkt.values/1e6, color=ACCENT_BLUE, alpha=0.18, label="Total market")
    ax2.plot(mkt.index, mkt.values/1e6, color=ACCENT_BLUE, linewidth=1.5)
    ax2.plot(boat_m.index, boat_m.values/1e6, color=BOAT_RED, linewidth=2.5, label="boAt")
    ax2.set_title("Monthly market vs boAt — Jan 2020 → present", loc="left", color=BOAT_BLACK)
    ax2.set_ylabel("Units (millions / month)")
    ax2.legend(loc="upper left", frameon=False)
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.grid(axis="y", linestyle=":", alpha=0.4)
    # Annotate latest point
    last_b = boat_m.iloc[-1] / 1e6
    ax2.annotate(f"{last_b:.1f}M\n{DATA_END:%b %Y}", xy=(boat_m.index[-1], last_b),
                 xytext=(-70, 22), textcoords="offset points",
                 fontsize=10, fontweight="bold", color=BOAT_RED,
                 arrowprops=dict(arrowstyle="->", color=BOAT_RED, lw=1))

    fig.savefig(OUT / "01_hero_dashboard.png", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 01_hero_dashboard.png")
    return dict(boat_share=boat_share, boat_units_12=boat_units_12,
                noise_units_12=noise_units_12, boat_yoy=boat_yoy, mkt_yoy=mkt_yoy,
                market_units_12=market_units_12)

# ----------------------------------------------------------------------------
# Chart 2 — Top 10 brands (last 12 months)
# ----------------------------------------------------------------------------
def top10():
    sub = units[units["month"] >= LAST12_START]
    top = sub.groupby("company")["value"].sum().sort_values(ascending=False).head(10)
    fig, ax = plt.subplots(figsize=(12, 7))
    names = [label(c) for c in top.index]
    colors = [BOAT_RED if c == "Imagine Marketing" else "#3C4858" for c in top.index]
    bars = ax.barh(names[::-1], (top.values/1e6)[::-1], color=colors[::-1], edgecolor="white")
    total = top.sum()
    for b, v, c in zip(bars, (top.values/1e6)[::-1], top.index[::-1]):
        share = v*1e6 / total * 100
        ax.text(v + 0.4, b.get_y() + b.get_height()/2,
                f"{v:.1f}M   ({share:4.1f}% of top 10)",
                va="center", fontsize=11, fontweight="bold",
                color=BOAT_RED if c == "Imagine Marketing" else INK)
    ax.set_xlim(0, top.values.max()/1e6 * 1.30)
    ax.set_title("Top 10 wearable brands in India by units shipped",
                 loc="left", fontsize=18, color=BOAT_BLACK, pad=28)
    ax.text(0, 1.02, f"Last 12 months ending {DATA_END:%b %Y} · Source: IDC",
            transform=ax.transAxes, fontsize=11, color="#666")
    ax.set_xlabel("Units shipped (millions)")
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    fig.savefig(OUT / "02_top10_last12mo.png", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 02_top10_last12mo.png")

# ----------------------------------------------------------------------------
# Chart 3 / 4 — Quarterly share trend for Earwear & Smartwatch
# ----------------------------------------------------------------------------
def share_trend(category: str, focus: list[str], filename: str, title_suffix: str):
    sub = units[units["product_category"] == category].copy()
    sub["quarter"] = sub["month"].dt.to_period("Q").dt.to_timestamp()
    q = sub.groupby(["quarter", "company"])["value"].sum().reset_index()
    q_total = q.groupby("quarter")["value"].sum().rename("total")
    q = q.merge(q_total, on="quarter")
    q["share"] = q["value"] / q["total"] * 100
    pivot = q.pivot(index="quarter", columns="company", values="share").fillna(0)
    pivot = pivot[[c for c in focus if c in pivot.columns]]

    fig, ax = plt.subplots(figsize=(13, 7))
    for i, co in enumerate(pivot.columns):
        col = BOAT_RED if co == "Imagine Marketing" else PALETTE[(i+1) % len(PALETTE)]
        lw  = 3.2 if co == "Imagine Marketing" else 1.8
        ax.plot(pivot.index, pivot[co], label=label(co), color=col, linewidth=lw,
                marker="o", markersize=4)
        # endpoint label
        ax.text(pivot.index[-1], pivot[co].iloc[-1] + 0.6, f"{label(co)} {pivot[co].iloc[-1]:.1f}%",
                color=col, fontsize=10, fontweight="bold")
    ax.set_title(f"{category}: quarterly market share — {title_suffix}",
                 loc="left", fontsize=18, color=BOAT_BLACK, pad=28)
    ax.text(0, 1.02, "Share of category units · Source: IDC India Monthly Wearable Tracker",
            transform=ax.transAxes, fontsize=11, color="#666")
    ax.set_ylabel("Share of category units")
    ax.yaxis.set_major_formatter(FuncFormatter(percent))
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.legend(loc="upper left", frameon=False, ncol=2)
    ax.set_xlim(pivot.index.min(), pivot.index.max() + pd.DateOffset(months=4))
    fig.savefig(OUT / filename, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {filename}")

# ----------------------------------------------------------------------------
# Chart 5 — Category mix evolution (stacked area)
# ----------------------------------------------------------------------------
def category_mix():
    cat = units.groupby(["month", "product_category"])["value"].sum().unstack(fill_value=0)
    cat = cat[["Earwear", "Smartwatch", "Wrist Band", "Rings", "Glasses", "Other"]]
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.stackplot(cat.index, [cat[c]/1e6 for c in cat.columns],
                 labels=cat.columns, colors=PALETTE[:len(cat.columns)], alpha=0.9)
    ax.set_title("India wearables — category mix has shifted dramatically",
                 loc="left", fontsize=18, color=BOAT_BLACK, pad=28)
    ax.text(0, 1.02, "Monthly units by product category · Source: IDC",
            transform=ax.transAxes, fontsize=11, color="#666")
    ax.set_ylabel("Units (millions / month)")
    ax.legend(loc="upper left", frameon=False, ncol=3)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    # Callout: Wrist band collapse
    ax.annotate("Wrist Bands\ncollapsed as\nSmartwatches\ntook over",
                xy=(pd.Timestamp("2022-06-01"), 3.2), xytext=(pd.Timestamp("2020-06-01"), 9.5),
                fontsize=10, color=INK, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#555"))
    fig.savefig(OUT / "05_category_mix_area.png", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 05_category_mix_area.png")

# ----------------------------------------------------------------------------
# Chart 6 — Total market size monthly
# ----------------------------------------------------------------------------
def market_size():
    mkt = units.groupby("month")["value"].sum().sort_index()
    rolling = mkt.rolling(3, center=True, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.bar(mkt.index, mkt.values/1e6, width=22, color="#C9D6E4", edgecolor="white", label="Monthly")
    ax.plot(rolling.index, rolling.values/1e6, color=BOAT_RED, linewidth=2.5, label="3-mo avg")
    ax.set_title("India wearables — total monthly units shipped",
                 loc="left", fontsize=18, color=BOAT_BLACK, pad=28)
    ax.text(0, 1.02, f"Jan 2020 → {DATA_END:%b %Y} · Source: IDC",
            transform=ax.transAxes, fontsize=11, color="#666")
    ax.set_ylabel("Units (millions)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="upper left", frameon=False)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    peak_idx = mkt.idxmax()
    ax.annotate(f"Peak: {mkt.max()/1e6:.1f}M\n{peak_idx:%b %Y}",
                xy=(peak_idx, mkt.max()/1e6),
                xytext=(-110, -40), textcoords="offset points",
                fontsize=10, fontweight="bold", color=INK,
                arrowprops=dict(arrowstyle="->", color="#555"))
    fig.savefig(OUT / "06_market_size_monthly.png", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 06_market_size_monthly.png")

# ----------------------------------------------------------------------------
# Chart 7 — boAt growth trajectory
# ----------------------------------------------------------------------------
def boat_growth():
    b = units.query("company == 'Imagine Marketing'").groupby("month")["value"].sum().sort_index()
    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.fill_between(b.index, b.values/1e6, color=BOAT_RED, alpha=0.15)
    ax.plot(b.index, b.values/1e6, color=BOAT_RED, linewidth=2.6)
    peak = b.idxmax()
    ax.annotate(f"All-time peak\n{b.max()/1e6:.2f}M units\n{peak:%b %Y}",
                xy=(peak, b.max()/1e6),
                xytext=(-110, -45), textcoords="offset points",
                fontsize=10, fontweight="bold", color=BOAT_RED,
                arrowprops=dict(arrowstyle="->", color=BOAT_RED))
    last = b.iloc[-1]
    ax.annotate(f"{DATA_END:%b %Y}\n{last/1e6:.2f}M",
                xy=(b.index[-1], last/1e6), xytext=(-90, 22),
                textcoords="offset points", fontsize=10, fontweight="bold",
                color=INK, arrowprops=dict(arrowstyle="->", color="#555"))
    ax.set_title("boAt monthly units shipped — the ride to #1",
                 loc="left", fontsize=18, color=BOAT_BLACK, pad=28)
    ax.text(0, 1.02, "Imagine Marketing · all categories combined · Source: IDC",
            transform=ax.transAxes, fontsize=11, color="#666")
    ax.set_ylabel("Units (millions / month)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    fig.savefig(OUT / "07_boat_growth.png", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 07_boat_growth.png")

# ----------------------------------------------------------------------------
# Chart 8 — Share heatmap (top brands × year, overall units)
# ----------------------------------------------------------------------------
def share_heatmap():
    df = units.copy()
    df["year"] = df["month"].dt.year
    yearly = df.groupby(["year", "company"])["value"].sum().reset_index()
    yr_total = yearly.groupby("year")["value"].sum().rename("total")
    yearly = yearly.merge(yr_total, on="year")
    yearly["share"] = yearly["value"] / yearly["total"] * 100
    top_brands = (yearly.groupby("company")["value"].sum()
                  .sort_values(ascending=False).head(10).index.tolist())
    pv = yearly[yearly["company"].isin(top_brands)].pivot(
        index="company", columns="year", values="share").fillna(0)
    pv = pv.reindex(top_brands)
    pv.index = [label(c) for c in pv.index]

    fig, ax = plt.subplots(figsize=(12, 6.5))
    im = ax.imshow(pv.values, cmap="Reds", aspect="auto", vmin=0, vmax=max(35, pv.values.max()))
    ax.set_xticks(range(pv.shape[1]))
    ax.set_xticklabels(pv.columns)
    ax.set_yticks(range(pv.shape[0]))
    ax.set_yticklabels(pv.index)
    for i in range(pv.shape[0]):
        for j in range(pv.shape[1]):
            v = pv.values[i, j]
            if v > 0.05:
                ax.text(j, i, f"{v:.1f}%", ha="center", va="center",
                        color="white" if v > 18 else INK, fontsize=10, fontweight="bold")
    ax.set_title("Market share by year — top 10 wearable brands",
                 loc="left", fontsize=18, color=BOAT_BLACK, pad=18)
    ax.text(0, -0.12, "Share of total India wearable units · Source: IDC",
            transform=ax.transAxes, fontsize=11, color="#666")
    plt.colorbar(im, ax=ax, fraction=0.025, pad=0.02).set_label("Share (%)")
    fig.savefig(OUT / "08_share_heatmap.png", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 08_share_heatmap.png")

# ----------------------------------------------------------------------------
# Chart 9 — Price positioning (ASP vs Volume) — last 12 months Smartwatch
# ----------------------------------------------------------------------------
def price_positioning():
    sw_units = units[(units["product_category"] == "Smartwatch") & (units["month"] >= LAST12_START)]
    sw_asp = asp_inr[(asp_inr["product_category"] == "Smartwatch") & (asp_inr["month"] >= LAST12_START)]
    vol = sw_units.groupby("company")["value"].sum()
    # Volume-weighted ASP: sum(asp*units)/sum(units) — need monthly join
    joined = sw_units.merge(sw_asp, on=["company", "month"], suffixes=("_u", "_p"))
    joined["spend"] = joined["value_u"] * joined["value_p"]
    grp = joined.groupby("company").agg(units=("value_u", "sum"), spend=("spend", "sum"))
    grp["asp"] = grp["spend"] / grp["units"]
    grp = grp[grp["units"] >= 50000].sort_values("units", ascending=False)

    fig, ax = plt.subplots(figsize=(12, 7.5))
    sizes = (grp["units"] / grp["units"].max()) * 4500 + 60
    for co, row in grp.iterrows():
        col = BOAT_RED if co == "Imagine Marketing" else "#5B6470"
        ax.scatter(row["asp"], row["units"]/1e6, s=sizes[co], alpha=0.65,
                   edgecolor="white", linewidth=1.5, color=col, zorder=3)
        ax.annotate(label(co), (row["asp"], row["units"]/1e6),
                    xytext=(7, 7), textcoords="offset points",
                    fontsize=10, fontweight="bold",
                    color=BOAT_RED if co == "Imagine Marketing" else INK)
    ax.set_title("Smartwatch positioning — price vs volume (last 12 months)",
                 loc="left", fontsize=18, color=BOAT_BLACK, pad=28)
    ax.text(0, 1.02, "Bubble size = units shipped · ASP in ₹ · Source: IDC",
            transform=ax.transAxes, fontsize=11, color="#666")
    ax.set_xlabel("Average Selling Price (₹)")
    ax.set_ylabel("Units shipped (millions, last 12 mo)")
    ax.grid(linestyle=":", alpha=0.4)
    # Quadrant guide
    med_asp = grp["asp"].median()
    med_vol = grp["units"].median()/1e6
    ax.axvline(med_asp, color="#cccccc", linestyle="--", linewidth=1)
    ax.axhline(med_vol, color="#cccccc", linestyle="--", linewidth=1)
    ax.text(0.99, 0.97, "Premium + Niche", transform=ax.transAxes, ha="right", va="top",
            fontsize=9, color="#888")
    ax.text(0.01, 0.97, "Value + Niche", transform=ax.transAxes, ha="left", va="top",
            fontsize=9, color="#888")
    ax.text(0.99, 0.02, "Premium + Mass", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=9, color="#888")
    ax.text(0.01, 0.02, "Value + Mass", transform=ax.transAxes, ha="left", va="bottom",
            fontsize=9, color="#888")
    fig.savefig(OUT / "09_price_positioning.png", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 09_price_positioning.png")

# ----------------------------------------------------------------------------
# Chart 10 — KID-FRIENDLY: simple share donut "who sold the most"
# ----------------------------------------------------------------------------
def kid_pie():
    sub = units[units["month"] >= LAST12_START]
    top = sub.groupby("company")["value"].sum().sort_values(ascending=False)
    top6 = top.head(6)
    other = top.iloc[6:].sum()
    series = pd.concat([top6, pd.Series({"Everyone else": other})])
    series.index = [label(c) for c in series.index]
    colors = [BOAT_RED, "#0B66C2", "#11A578", "#F39C12", "#7A3FB8", "#34495E", "#BDC3C7"]

    fig, ax = plt.subplots(figsize=(11, 8))
    wedges, _ = ax.pie(series.values, colors=colors, startangle=90,
                       wedgeprops=dict(width=0.42, edgecolor="white", linewidth=3))
    total = series.sum()
    ax.text(0, 0.08, "Out of every 100\nwearables sold\nin India…", ha="center",
            fontsize=14, color=INK)
    ax.text(0, -0.18, f"…{series.iloc[0]/total*100:.0f} were boAt!",
            ha="center", fontsize=20, color=BOAT_RED, fontweight="bold")
    # Legend with percentages
    legend_labels = [f"{n}  —  {v/total*100:.1f}%" for n, v in series.items()]
    ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(1.02, 0.5),
              frameon=False, fontsize=12)
    ax.set_title("Last 12 months: who sold the most wearables in India?",
                 fontsize=18, color=BOAT_BLACK, pad=18)
    fig.savefig(OUT / "10_kid_simple_share_pie.png", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 10_kid_simple_share_pie.png")

# -------------------------------------------------------------------------
print("\nGenerating charts…")
kpis = hero()
top10()
share_trend("Earwear",
            focus=["Imagine Marketing", "OPPO", "GoBoult", "Nexxbase", "Samsung", "Nothing"],
            filename="03_earwear_share_trend.png",
            title_suffix="boAt holds the lead")
share_trend("Smartwatch",
            focus=["Nexxbase", "Imagine Marketing", "Fire - Boltt", "Titan", "GoBoult", "SRK Powertech"],
            filename="04_smartwatch_share_trend.png",
            title_suffix="Noise leads · boAt slipped to #3")
category_mix()
market_size()
boat_growth()
share_heatmap()
price_positioning()
kid_pie()

# Save KPIs for the report
import json
(ROOT / "data" / "clean" / "kpis.json").write_text(
    json.dumps({k: float(v) for k, v in kpis.items()} | {"data_end": DATA_END.strftime("%Y-%m")}, indent=2),
    encoding="utf-8")
print(f"\n✔ All charts saved to {OUT}")
