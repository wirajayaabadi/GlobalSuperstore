import streamlit as st

from utils import charts as ch
from utils import metrics as m
from utils import ui
from utils.data_loader import get_filtered_data

fd = get_filtered_data()
ui.require_data(fd)

df = fd.df
tot = m.summarize(df)
bands = m.discount_band_summary(df)
matrix = m.market_band_matrix(df)
split = m.market_margin_split(df)
yearly = m.yearly_summary(df)
countries = m.country_summary(df)
countries_n = countries[countries["Lines"] >= 50]

r_line = m.correlation(df["Discount"], df["Line Margin"])
r_country = m.correlation(countries_n["DeepShare"], countries_n["Margin"])

loss_bands = bands[bands["Margin"] < 0]
first_loss = loss_bands.iloc[0]["Band"] if len(loss_bands) else None
if first_loss is not None and m._finite(tot["deep_margin"]) and tot["deep_margin"] < 0:
    headline = "Margin turns negative from the %s discount band; above 30%% off, lines lose %s cents per dollar sold" % (
        first_loss, "%.0f" % (abs(tot["deep_margin"]) * 100))
elif first_loss is not None:
    headline = "Margin turns negative from the %s discount band" % first_loss
else:
    headline = "No discount band is loss-making in this selection"
summary = ("Line-level discount and line margin show a %s correlation (r = %s). Lines discounted above 30%% are %s of "
           "all lines; without them the remaining lines earn a %s margin instead of %s." % (
               m.strength(r_line), "%.2f" % r_line if m._finite(r_line) else "n/a", m.fmt_pct(tot["deep_share"]),
               m.fmt_pct(tot["rest_margin"]), m.fmt_pct(tot["margin"])))
ui.page_header("Profitability and root cause", headline, summary, fd)

# ---- driver 1: discount band economics
c1, c2 = st.columns(2)
with c1:
    over50 = bands.loc[bands["Band"] == ">50%"]
    note = ""
    if len(over50) and over50.iloc[0]["Lines"] > 0:
        note = "Above 50%% off, %s of lines lose money." % m.fmt_pct(over50.iloc[0]["LossShare"], 0)
    ui.chart_card("Every step up in discount lowers margin", "Profit margin by discount band; labels show the share of lines that lose money",
                  ch.create_profitability_chart(bands), key="rc_bands", note=note)
with c2:
    ui.chart_card(
        "Countries that discount more earn less (r = %s across %d countries)" % (
            "%.2f" % r_country if m._finite(r_country) else "n/a", len(countries_n)),
        "Each bubble is a country with at least 50 order lines; size = sales; dashed line = linear fit",
        ch.create_country_scatter(countries_n), key="rc_scatter",
        note="Correlation shows association, not causation: other country factors may also play a role.")

# ---- driver 2: the pattern holds in every market
neg_cells = int((matrix < 0).sum().sum())
valid_cells = int(matrix.notna().sum().sum())
deep_cols = [c for c in matrix.columns if c in ("31-40%", "41-50%", ">50%")]
deep_cells = matrix[deep_cols].stack().dropna()
if len(deep_cells) and (deep_cells < 0).all():
    heat_title = "The same pattern holds inside every market: all deep-discount cells are loss-making"
else:
    heat_title = "%d of %d market x deep-discount cells are loss-making" % (int((deep_cells < 0).sum()), len(deep_cells))
ui.chart_card(
    heat_title,
    "Profit margin by market (rows, weakest at top) and discount band (columns). Blank = fewer than 30 lines. "
    "%d of %d populated cells are negative." % (neg_cells, valid_cells),
    ch.create_heatmap(matrix), key="rc_heatmap")

c3, c4 = st.columns(2)
with c3:
    lo = split["Excluding deep discounts"].min()
    hi = split["Excluding deep discounts"].max()
    ui.chart_card(
        "On lines discounted 30%% or less, every market earns %s-%s" % (m.fmt_pct(lo, 0), m.fmt_pct(hi, 0)),
        "Actual margin (grey) vs margin on lines discounted 30% or less (blue), by market",
        ch.create_dumbbell(split), key="rc_dumbbell",
        note="Mechanical comparison on existing lines, not a forecast: some deep-discount volume would be lost at higher prices.")
with c4:
    if len(yearly) >= 2 and yearly["DeepProfit"].iloc[-1] < yearly["DeepProfit"].iloc[0] < 0:
        title = "Deep-discount share stayed at %s-%s of lines while losses grew with volume" % (
            m.fmt_pct(yearly["DeepShare"].min(), 0), m.fmt_pct(yearly["DeepShare"].max(), 0))
    else:
        title = "Net profit on deep-discount lines"
    ui.chart_card(title, "Net profit on lines discounted above 30%, by year",
                  ch.create_deep_discount_trend_chart(yearly), key="rc_deep")

# ---- alternative explanations checked
ui.section("Alternative explanations checked",
           "Delivery speed changes what shipping costs, but freight is charged at much the same rate on profitable "
           "and loss-making lines")
ship = m.group_summary(df, "Ship Mode")
prio = m.group_summary(df, "Order Priority")
seg = m.group_summary(df, "Segment")
ship_freight = m.shipping_summary(df, "Ship Mode")
band_freight = m.shipping_summary(df, "Discount Band")
company_burden = m.safe_div(df["Shipping Cost"].sum(), df["Sales"].sum())
ship_margin_spread = ship["Margin"].max() - ship["Margin"].min()
burden_spread = ship_freight["ShipBurden"].max() - ship_freight["ShipBurden"].min()
band_burden_spread = band_freight["ShipBurden"].max() - band_freight["ShipBurden"].min()

f1, f2 = st.columns(2)
with f1:
    ui.chart_card("Ship Mode: margin spread %s" % m.fmt_pp(ship_margin_spread).lstrip("+"),
                  "Profit margin; dotted line = company margin",
                  ch.create_factor_chart(ship, "Ship Mode", tot["margin"]), key="rc_ship",
                  note="Margin varies by %s across delivery speeds, against %s across discount bands." % (
                      m.fmt_pp(ship_margin_spread).lstrip("+"),
                      m.fmt_pp(bands["Margin"].max() - bands["Margin"].min()).lstrip("+")))
with f2:
    fastest = ship_freight.sort_values("ShipBurden").iloc[-1]
    cheapest = ship_freight.sort_values("ShipBurden").iloc[0]
    ui.chart_card(
        "Ship Mode: shipping costs %s of sales on %s vs %s on %s" % (
            m.fmt_pct(fastest["ShipBurden"], 0), fastest["Ship Mode"],
            m.fmt_pct(cheapest["ShipBurden"], 0), cheapest["Ship Mode"]),
        "Shipping cost as a share of sales; dotted line = company average",
        ch.create_shipping_burden_chart(ship_freight, "Ship Mode", company_burden), key="rc_ship_freight",
        note="Freight is measured against sales because the data does not say whether Profit already nets shipping "
             "off, so this needs no assumption about how Profit was built.")

f3, f4 = st.columns(2)
for col, data, label, key in ((f3, prio, "Order Priority", "rc_prio"), (f4, seg, "Segment", "rc_seg")):
    spread = data["Margin"].max() - data["Margin"].min()
    with col:
        ui.chart_card("%s: margin spread %s" % (label, m.fmt_pp(spread).lstrip("+")),
                      "Profit margin; dotted line = company margin", ch.create_factor_chart(data, label, tot["margin"]),
                      key=key)

band_spread = bands["Margin"].max() - bands["Margin"].min()
st.caption(ui.md(
    "For comparison, the margin spread across discount bands is %s. Shipping burden is the mirror image: it varies by "
    "%s across delivery speeds but only %s across discount bands, so freight is charged at much the same rate on "
    "profitable and loss-making lines alike." % (
        m.fmt_pp(band_spread).lstrip("+"), m.fmt_pp(burden_spread).lstrip("+"),
        m.fmt_pp(band_burden_spread).lstrip("+"))))

other_spread = max(d["Margin"].max() - d["Margin"].min() for d in (ship, prio, seg))
if m._finite(tot["deep_margin"]) and tot["deep_share"] > 0:
    freight_clause = ("Freight is the one operational factor that does vary - it costs %s of sales more on the "
                      "fastest delivery speed than the slowest - but it is charged at nearly the same rate regardless "
                      "of discount (%s spread across bands), so it cannot account for lines that lose %s cents per "
                      "dollar." % (m.fmt_pp(burden_spread).lstrip("+"), m.fmt_pp(band_burden_spread).lstrip("+"),
                                   "%.0f" % (abs(tot["deep_margin"]) * 100)))
else:
    freight_clause = ("Freight costs %s of sales more on the fastest delivery speed than the slowest, but varies by "
                      "only %s across discount bands, so it is charged at much the same rate whatever the discount." % (
                          m.fmt_pp(burden_spread).lstrip("+"), m.fmt_pp(band_burden_spread).lstrip("+")))
ui.insight_box(
    title="Root-cause conclusion",
    finding="Margin falls as discount rises (%s correlation at line level). Deep-discount lines (>30%%) are "
            "%s of lines and net %s; %s of %s market x deep-discount cells are loss-making, while ship mode, priority "
            "and segment move margin by at most %s. %s" % (
                m.strength(r_line), m.fmt_pct(tot["deep_share"]), m.fmt_money(tot["deep_profit"]),
                int((deep_cells < 0).sum()), len(deep_cells), m.fmt_pp(other_spread).lstrip("+"), freight_clause),
    implication="The evidence is consistent with one root cause: there is no floor on how far a line can be discounted. "
                "Because the deep-discount share is stable, the loss scales with growth - which is why margin stays flat.",
    action="Eliminate discounts above 50% immediately, then pilot a 20% ceiling with approval for exceptions in the two "
           "heaviest-discounting markets before a global rollout, and monitor deep-discount share as a leading KPI. "
           "The dataset has no cost or competitor data, so the pilot is what validates price elasticity.",
)
