import pandas as pd
import streamlit as st

from utils import metrics as m
from utils import ui
from utils.data_loader import get_filtered_data

fd = get_filtered_data()
ui.require_data(fd)

df = fd.df
tot = m.summarize(df)
yearly = m.yearly_summary(df)
bands = m.discount_band_summary(df)
split = m.market_margin_split(df)
countries = m.country_summary(df)
losers = countries[countries["Profit"] < 0]
subcats = m.group_summary(df, "Sub-Category")
worst_sub = subcats.sort_values("Profit").iloc[0]
factor_spread = max(m.group_summary(df, c)["Margin"].pipe(lambda s: s.max() - s.min())
                    for c in ("Ship Mode", "Order Priority", "Segment"))

# Highest discount band that is still profitable, counted from 0% upward
UPPER = {"0%": 0, "1-10%": 10, "11-20%": 20, "21-30%": 30, "31-40%": 40, "41-50%": 50, ">50%": 85}
ceiling = 0
for _, row in bands.iterrows():
    if row["Lines"] == 0:
        continue
    if row["Margin"] > 0:
        ceiling = UPPER[str(row["Band"])]
    else:
        break

cagr = m.calculate_cagr(yearly["Sales"].iloc[0], yearly["Sales"].iloc[-1], len(yearly) - 1)
dm = yearly["Margin"].iloc[-1] - yearly["Margin"].iloc[0] if len(yearly) >= 2 else float("nan")
given_away = -tot["deep_profit"]

headline = ("%s of profit was given away on lines discounted above 30%%" % m.fmt_money(given_away)
            if given_away > 0 else "Deep discounts are not loss-making in this selection")
summary = ("The recommendations below follow directly from the evidence on the previous pages. Each finding separates the "
           "fact (from the data), the interpretation (our reading) and the recommendation (proposed action).")
ui.page_header("Strategic insights", headline, summary, fd)

# ---- value at stake
ui.section("Value at stake", "Mechanical figures from existing order lines - not a forecast")
with st.container(horizontal=True):
    st.metric("Net profit on lines > 30% off", m.fmt_money(tot["deep_profit"]), border=True,
              help="Sum of Profit on lines with Discount > 30%.")
    st.metric("Profit on all other lines", m.fmt_money(tot["rest_profit"]), border=True,
              help="Sum of Profit on lines with Discount <= 30%.")
    st.metric("Actual margin", m.fmt_pct(tot["margin"]), border=True, help="Total Profit / total Sales.")
    st.metric("Margin excl. deep-discount lines", m.fmt_pct(tot["rest_margin"]),
              m.fmt_pp(tot["rest_margin"] - tot["margin"]) if m._finite(tot["rest_margin"]) else None,
              border=True, help="Profit / Sales on lines with Discount <= 30%. Upper bound: repricing would lose some volume.")
    st.metric("Loss-making countries", "%d" % len(losers), m.fmt_money(losers["Profit"].sum()) + " net",
              delta_color="off", delta_arrow="off", border=True)

# ---- findings
ui.section("Key findings")
g1, g2 = st.columns(2)
with g1:
    ui.fir_card(
        1, "Growth has not improved profitability per dollar",
        "Sales grew %s a year (CAGR %d-%d); margin moved %s, from %s to %s." % (
            m.fmt_pct(cagr), fd.start, fd.end, m.fmt_pp(dm), m.fmt_pct(yearly["Margin"].iloc[0]),
            m.fmt_pct(yearly["Margin"].iloc[-1])) if len(yearly) >= 2 else
        "Only one year selected: margin %s." % m.fmt_pct(tot["margin"]),
        "The business is getting bigger, not better: each new dollar of sales carries the same mix of healthy and "
        "loss-making lines.",
        "Report margin and deep-discount share alongside sales at every board review.")
    ui.fir_card(
        3, "The problem is a policy, not a market",
        "On lines discounted 30%% or less, every market earns %s to %s; actual market margins range %s to %s." % (
            m.fmt_pct(split["Excluding deep discounts"].min()), m.fmt_pct(split["Excluding deep discounts"].max()),
            m.fmt_pct(split["Overall"].min()), m.fmt_pct(split["Overall"].max())),
        "No market appears structurally unprofitable at normal prices; the gap is associated with how deeply each "
        "market discounts.",
        "Fix discount policy globally before considering market exits.")
    ui.fir_card(
        5, "Operations and customer mix are not the lever",
        "Ship mode, order priority and segment each move margin by at most %s, versus %s across discount bands." % (
            m.fmt_pp(factor_spread).lstrip("+"), m.fmt_pp(bands["Margin"].max() - bands["Margin"].min()).lstrip("+")),
        "Logistics or segment programmes would address a small part of the margin gap.",
        "Keep management attention on pricing; treat logistics as a separate efficiency agenda.")
with g2:
    ui.fir_card(
        2, "Deep discounts destroy value",
        "Lines discounted above 30%% are %s of lines, bring %s of sales and net %s (margin %s)." % (
            m.fmt_pct(tot["deep_share"]), m.fmt_money(tot["deep_sales"]), m.fmt_money(tot["deep_profit"]),
            m.fmt_pct(tot["deep_margin"])),
        "On average these lines are sold below cost: the more of them we sell, the more profit we lose.",
        "Cap discounts at %d%% (the highest band that is still profitable) and require approval above it." % ceiling
        if ceiling > 0 else "Review every discounted line; even low discount bands are loss-making in this selection.")
    ui.fir_card(
        4, "Losses are concentrated and identifiable",
        "%d countries lose %s in total; %s is the weakest sub-category at %s (%s margin)." % (
            len(losers), m.fmt_money(abs(losers["Profit"].sum())), worst_sub["Sub-Category"],
            m.fmt_money(worst_sub["Profit"]), m.fmt_pct(worst_sub["Margin"])),
        "A short, named list of countries and products explains most of the damage, which makes action tractable.",
        "Run a 90-day fix-or-exit review for loss-making countries and remove deep-discount eligibility for %s." %
        worst_sub["Sub-Category"])

# ---- action plan
ui.section("Priority actions", "Owners and timing are proposals for management discussion")
plan = pd.DataFrame([
    {"Priority": 1, "Action": "Discount ceiling at %d%% with approval workflow above it" % max(ceiling, 10),
     "Evidence": "Margin by discount band; %s of lines above 30%% off" % m.fmt_pct(tot["deep_share"]),
     "Owner (proposed)": "CFO + Head of Sales", "KPI to track": "Deep-discount share, margin",
     "Timing (proposed)": "Next quarter"},
    {"Priority": 2, "Action": "Fix-or-exit review of %d loss-making countries" % len(losers),
     "Evidence": "Country ranking; %s combined loss" % m.fmt_money(abs(losers["Profit"].sum())),
     "Owner (proposed)": "Regional GMs", "KPI to track": "Country margin after repricing",
     "Timing (proposed)": "90 days"},
    {"Priority": 3, "Action": "Remove deep-discount eligibility for %s and top loss-making SKUs" % worst_sub["Sub-Category"],
     "Evidence": "Product page loss table", "Owner (proposed)": "Category management",
     "KPI to track": "Sub-category margin", "Timing (proposed)": "Next quarter"},
    {"Priority": 4, "Action": "Add margin and deep-discount share to the monthly board pack",
     "Evidence": "Flat margin despite growth", "Owner (proposed)": "FP&A",
     "KPI to track": "Margin trend", "Timing (proposed)": "Immediately"},
])
st.dataframe(plan, hide_index=True, column_config={
    "Priority": st.column_config.NumberColumn(width="small"),
    "Action": st.column_config.TextColumn(width="large"),
    "Evidence": st.column_config.TextColumn(width="medium"),
})

with st.expander("Limitations and next analyses", icon=":material/info:"):
    st.markdown(ui.md(
        "- **Association, not causation.** Correlations between discount and margin do not prove that removing "
        "discounts keeps the same volume. A price-elasticity pilot in one or two markets should precede a global rollout.\n"
        "- **No cost, competitor or campaign data.** We cannot see why discounts were granted (clearance, competition, "
        "key accounts).\n"
        "- **Shipping cost** is reported per line but the dataset does not state whether it is already deducted from "
        "Profit or who bears it, so it is excluded from the profit analysis.\n"
        "- **Customer IDs are region-specific** (%s IDs for %s names), so customer-level metrics are not used.\n"
        "- **Next:** price-elasticity pilot, discount approval audit trail, customer-level profitability once IDs are "
        "consolidated." % ("{:,}".format(df["Customer ID"].nunique()), "{:,}".format(df["Customer Name"].nunique()))
    ))
