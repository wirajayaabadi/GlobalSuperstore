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

# Supporting facts for the phased plan
over50 = bands.loc[bands["Band"] == ">50%"].iloc[0]
over50_sales_share = m.safe_div(over50["Sales"], tot["sales"])
markets = m.group_summary(df, "Market")
pilot = markets.sort_values("DeepShare", ascending=False).head(2)
pilot_names = " and ".join(pilot["Market"].tolist()) if len(pilot) else "the two heaviest-discounting markets"
top_losers = losers.head(4)
top_losers_share = m.safe_div(top_losers["Profit"].sum(), losers["Profit"].sum())
ship_spread = m.group_summary(df, "Ship Mode")["Margin"].pipe(lambda s: s.max() - s.min())
ship_freight = m.shipping_summary(df, "Ship Mode")
band_freight = m.shipping_summary(df, "Discount Band")
burden_spread = ship_freight["ShipBurden"].max() - ship_freight["ShipBurden"].min()
band_burden_spread = band_freight["ShipBurden"].max() - band_freight["ShipBurden"].min()
cats = m.group_summary(df, "Category")
weak_cat = cats.sort_values("Margin").iloc[0]
weak_cat_rest = m.summarize(df[(df["Category"] == weak_cat["Category"]) & (~df["Deep Discount"])])
worst_sub_rest = m.summarize(df[(df["Sub-Category"] == worst_sub["Sub-Category"]) & (~df["Deep Discount"])])
period = "%d-%d" % (fd.start, fd.end) if fd.n_years > 1 else str(fd.end)
period_phrase = "between %d and %d" % (fd.start, fd.end) if fd.n_years > 1 else "in %d" % fd.end

headline = ("%s of profit was given away on lines discounted above 30%%" % m.fmt_money(given_away)
            if given_away > 0 else "Deep discounts are not loss-making in this selection")
summary = ("The analysis identifies a clear profitability issue: excessive discounting rather than weak underlying demand "
           "is eroding the company's margins. Order lines discounted above 30%% account for %s of all lines and "
           "generated %s in losses %s, while lines discounted at 30%% or below achieved a %s profit margin. "
           "The evidence therefore suggests that the company's profitability challenge is primarily a "
           "discount-governance problem." % (
               m.fmt_pct(tot["deep_share"]), m.fmt_money(abs(tot["deep_profit"])), period_phrase,
               m.fmt_pct(tot["rest_margin"]))) if given_away > 0 else (
           "In this selection deep discounts do not destroy value; the findings and actions below are shown for "
           "completeness and should be read against the company-wide view.")
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
    st.metric("Lines discounted > 50%", "{:,}".format(int(over50["Lines"])),
              "%s loss-making" % m.fmt_pct(over50["LossShare"], 0) if over50["Lines"] > 0 else None,
              delta_color="off", delta_arrow="off", border=True,
              help="Order lines with Discount > 50%. Share of those lines with negative profit.")
    st.metric("Net profit on lines > 50% off", m.fmt_money(over50["Profit"]), border=True,
              help="Sum of Profit on lines with Discount > 50%%. These lines are %s of sales." % m.fmt_pct(over50_sales_share))
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
        ("Eliminate discounts above 50%% now, then pilot a %d%% ceiling (the highest band that is still profitable) with "
         "management approval for exceptions in %s before a global rollout." % (ceiling, pilot_names))
        if ceiling > 0 else "Review every discounted line; even low discount bands are loss-making in this selection.")
    ui.fir_card(
        4, "Losses are concentrated and identifiable",
        "%d countries lose %s in total; %s is the weakest sub-category at %s (%s margin)." % (
            len(losers), m.fmt_money(abs(losers["Profit"].sum())), worst_sub["Sub-Category"],
            m.fmt_money(worst_sub["Profit"]), m.fmt_pct(worst_sub["Margin"])),
        "A short, named list of countries and products explains most of the damage, which makes action tractable.",
        ("Reprice the largest loss-making countries (%s) and %s first rather than exiting markets or delisting "
         "products; consider exit only if a country is still loss-making after two quarters under the discount ceiling."
         % (", ".join(top_losers["Country"].tolist()) if len(top_losers) else "none in this selection",
            worst_sub["Sub-Category"])))

# ---- phased action plan
ui.section("Phased response",
           "Sequenced so that zero-risk steps come first and the policy change is tested before it is scaled. "
           "Owners and timing are proposals for management discussion; value at stake is mechanical, not a forecast.")
ceiling_label = "%d%%" % ceiling if ceiling > 0 else "a low"
plan = pd.DataFrame([
    {"Phase": "1", "Action": "Eliminate all discounts above 50% immediately",
     "Evidence": "%s lines above 50%% off; %s loss-making; net %s" % (
         "{:,}".format(int(over50["Lines"])), m.fmt_pct(over50["LossShare"], 0), m.fmt_money(over50["Profit"])),
     "Baseline -> Target": "%s lines -> 0" % "{:,}".format(int(over50["Lines"])),
     "Value at stake": "%s (%s of sales at risk)" % (m.fmt_money(abs(over50["Profit"])), m.fmt_pct(over50_sales_share)),
     "Owner (proposed)": "Sales Operations + CFO", "Timing": "0-30 days"},
    {"Phase": "1", "Action": "Add profit margin, deep-discount share and discount exceptions to the monthly Board review",
     "Evidence": "Margin moved %s while sales grew %s a year" % (m.fmt_pp(dm), m.fmt_pct(cagr)),
     "Baseline -> Target": "Not reported -> reported monthly",
     "Value at stake": "Enabler for phases 2-4",
     "Owner (proposed)": "FP&A", "Timing": "0-30 days"},
    {"Phase": "2", "Action": "Pilot a %s discount ceiling with management approval for exceptions in %s" % (ceiling_label, pilot_names),
     "Evidence": "Highest deep-discount share: %s" % "; ".join(
         "%s %s (margin %s)" % (r["Market"], m.fmt_pct(r["DeepShare"], 0), m.fmt_pct(r["Margin"])) for _, r in pilot.iterrows()),
     "Baseline -> Target": "Deep share %s -> <5%%; margin %s -> >=15%% in pilot markets" % (
         m.fmt_pct(tot["deep_share"]), m.fmt_pct(tot["margin"])),
     "Value at stake": "Measures volume retention; %s lost on 31-50%% band" % m.fmt_money(
         abs(bands.loc[bands["Band"].isin(["31-40%", "41-50%"]), "Profit"].sum())),
     "Owner (proposed)": "Head of Sales + FP&A", "Timing": "30-120 days (one full quarter)"},
    {"Phase": "3", "Action": "Reprice the largest loss-making countries and products first; no market exit or delisting",
     "Evidence": "%s = %s of country losses; %s earns %s on lines discounted 30%% or less" % (
         ", ".join(top_losers["Country"].tolist()) if len(top_losers) else "no loss-making country",
         m.fmt_pct(top_losers_share, 0), worst_sub["Sub-Category"], m.fmt_money(worst_sub_rest["profit"])),
     "Baseline -> Target": "%d loss-making countries -> 0 after two quarters under the ceiling" % len(losers),
     "Value at stake": "%s (countries) + %s (%s)" % (
         m.fmt_money(abs(losers["Profit"].sum())), m.fmt_money(abs(min(worst_sub["Profit"], 0))), worst_sub["Sub-Category"]),
     "Owner (proposed)": "Regional GMs + Category management", "Timing": "30-180 days"},
    {"Phase": "4", "Action": "Scale the discount ceiling globally if the pilot retains at least 80% of sales volume",
     "Evidence": "Lines discounted 30%% or less earn %s vs %s overall" % (m.fmt_pct(tot["rest_margin"]), m.fmt_pct(tot["margin"])),
     "Baseline -> Target": "Company margin %s -> 15-18%% (upper bound %s)" % (m.fmt_pct(tot["margin"]), m.fmt_pct(tot["rest_margin"])),
     "Value at stake": "%s over %s" % (m.fmt_money(abs(tot["deep_profit"])), period),
     "Owner (proposed)": "CFO", "Timing": "Quarter after the pilot"},
])
st.dataframe(plan, hide_index=True, column_config={
    "Phase": st.column_config.TextColumn(width="small"),
    "Action": st.column_config.TextColumn(width="large"),
    "Evidence": st.column_config.TextColumn(width="large"),
    "Baseline -> Target": st.column_config.TextColumn(width="medium"),
    "Value at stake": st.column_config.TextColumn(width="medium"),
})

# ---- what not to do
with st.container(border=True):
    st.markdown(":material/block: **What we recommend not doing**")
    st.markdown(ui.md(
        "- **Do not treat logistics as the fix for margin.** Freight is worth managing on its own merits - it costs "
        "%s of sales more on the fastest delivery speed than the slowest - but it is charged at nearly the same rate "
        "on profitable and loss-making lines (%s spread across discount bands), and margin varies by only %s across "
        "delivery speeds. Cutting shipping would trim cost without touching the loss.\n"
        "- **Do not exit the %d loss-making countries as a group.** They lose money because of discounts, not because "
        "of their markets: on lines discounted 30%% or less every market earns %s to %s.\n"
        "- **Do not remove %s from the catalogue.** At normal prices (30%% off or less) the category earns a %s margin."
        % (m.fmt_pp(burden_spread).lstrip("+"), m.fmt_pp(band_burden_spread).lstrip("+"),
           m.fmt_pp(ship_spread).lstrip("+"), len(losers), m.fmt_pct(split["Excluding deep discounts"].min()),
           m.fmt_pct(split["Excluding deep discounts"].max()), weak_cat["Category"], m.fmt_pct(weak_cat_rest["margin"]))))

with st.expander("Limitations and next analyses", icon=":material/info:"):
    st.markdown(ui.md(
        "- **Association, not causation.** Correlations between discount and margin do not prove that removing "
        "discounts keeps the same volume. A price-elasticity pilot in one or two markets should precede a global rollout.\n"
        "- **No cost, competitor or campaign data.** We cannot see why discounts were granted (clearance, competition, "
        "key accounts).\n"
        "- **Shipping cost** is reported per line but the dataset does not state whether it is already deducted from "
        "Profit or who bears it. It is therefore never subtracted from Profit; it is shown only as a share of sales, "
        "which measures how freight-heavy each delivery speed is without assuming how Profit was built.\n"
        "- **Customer IDs are region-specific** (%s IDs for %s names), so customer-level metrics are not used.\n"
        "- **Next:** price-elasticity pilot, discount approval audit trail, customer-level profitability once IDs are "
        "consolidated." % ("{:,}".format(df["Customer ID"].nunique()), "{:,}".format(df["Customer Name"].nunique()))
    ))
