import streamlit as st

from utils import charts as ch
from utils import metrics as m
from utils import ui
from utils.data_loader import get_filtered_data

fd = get_filtered_data()
ui.require_data(fd)

tot = m.summarize(fd.df)
markets = m.group_summary(fd.df, "Market").sort_values("Profit", ascending=False)
segments = m.group_summary(fd.df, "Segment").sort_values("Sales", ascending=False)
countries = m.country_summary(fd.df)
losers = countries[countries["Profit"] < 0].sort_values("Profit")

top = markets.iloc[0]
low_margin = markets.sort_values("Margin").iloc[0]
headline = "%s generates the most profit (%s); %d of %d countries lose money" % (
    top["Market"], m.fmt_money(top["Profit"]), len(losers), len(countries))
summary = ("Loss-making countries account for %s of sales and a combined loss of %s. The weakest market margin is %s "
           "at %s, against %s for the company." % (
               m.fmt_pct(losers["Sales"].sum() / tot["sales"] if tot["sales"] else float("nan")),
               m.fmt_money(abs(losers["Profit"].sum())), low_margin["Market"], m.fmt_pct(low_margin["Margin"]),
               m.fmt_pct(tot["margin"])))
ui.page_header("Markets and segments", headline, summary, fd)

# ---- map
with st.container(border=True):
    st.markdown("**Where profit is made and lost, country by country**")
    st.caption("Country view. Switch metric with the tabs. Blue = profit, red = loss.")
    t1, t2, t3 = st.tabs(["Profit", "Sales", "Margin"])
    with t1:
        st.plotly_chart(ch.create_choropleth(countries, "Profit"), config=ui.PLOTLY_CONFIG, key="mk_map_p")
    with t2:
        st.plotly_chart(ch.create_choropleth(countries, "Sales"), config=ui.PLOTLY_CONFIG, key="mk_map_s")
    with t3:
        st.plotly_chart(ch.create_choropleth(countries, "Margin"), config=ui.PLOTLY_CONFIG, key="mk_map_m")

# ---- markets
c1, c2 = st.columns(2)
with c1:
    big = markets.sort_values("Sales", ascending=False).iloc[0]
    ui.chart_card(
        "%s is the largest market by sales; %s has the lowest margin" % (big["Market"], low_margin["Market"]),
        "Sales (x) vs profit margin (y); bubble size = absolute profit",
        ch.create_market_bubble(markets, tot["margin"]), key="mk_bubble")
with c2:
    ui.chart_card(
        "Profit by market: %s and %s together deliver %s of profit" % (
            markets.iloc[0]["Market"], markets.iloc[1]["Market"] if len(markets) > 1 else "-",
            m.fmt_pct(markets.head(2)["Profit"].sum() / tot["profit"] if tot["profit"] else float("nan"))),
        "Total profit by market, ranked",
        ch.create_ranked_bar(markets, "Market", "Profit", height=340), key="mk_rank")

# ---- segments | loss countries
c3, c4 = st.columns([2, 3])
with c3:
    with st.container(border=True):
        spread = segments["Margin"].max() - segments["Margin"].min()
        st.markdown("**Segments behave alike: margins differ by only %s**" % ui.md(m.fmt_pp(spread).lstrip("+"))
                    if spread < 0.02 else "**Segment comparison**")
        st.caption("Sales, profit and average discount by customer segment")
        st.dataframe(
            segments[["Segment", "Sales", "Sales share", "Profit", "Margin", "AvgDiscount"]],
            hide_index=True,
            column_config={
                "Sales": st.column_config.NumberColumn(format="dollar"),
                "Sales share": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
                "Profit": st.column_config.NumberColumn(format="dollar"),
                "Margin": st.column_config.NumberColumn(format="percent"),
                "AvgDiscount": st.column_config.NumberColumn("Avg discount", format="percent"),
            },
        )
with c4:
    if len(losers):
        top_l = losers.head(15)
        ui.chart_card(
            "The %d largest loss-makers lose %s; %s alone loses %s" % (
                len(top_l), m.fmt_money(abs(top_l["Profit"].sum())), top_l.iloc[0]["Country"],
                m.fmt_money(abs(top_l.iloc[0]["Profit"]))),
            "Countries with negative total profit (largest losses)",
            ch.create_ranked_bar(top_l.sort_values("Profit", ascending=False), "Country", "Profit", height=380),
            key="mk_losers")
    else:
        with st.container(border=True):
            st.success("No country is loss-making in the current selection.", icon=":material/check_circle:")

with st.expander("Country table", icon=":material/table:"):
    st.dataframe(
        countries.sort_values("Sales", ascending=False)[["Country", "Market", "Sales", "Profit", "Margin", "DeepShare", "Orders"]],
        hide_index=True,
        column_config={
            "Sales": st.column_config.NumberColumn(format="dollar"),
            "Profit": st.column_config.NumberColumn(format="dollar"),
            "Margin": st.column_config.NumberColumn(format="percent"),
            "DeepShare": st.column_config.NumberColumn("Lines > 30% off", format="percent"),
            "Orders": st.column_config.NumberColumn(format="localized"),
        },
    )

worst_deep = markets.sort_values("DeepShare", ascending=False).iloc[0]
ui.insight_box(
    finding="%d countries are loss-making in aggregate. %s has both the lowest margin (%s) and the highest share of lines "
            "discounted above 30%% (%s)." % (len(losers), worst_deep["Market"], m.fmt_pct(worst_deep["Margin"]),
                                             m.fmt_pct(worst_deep["DeepShare"]))
    if worst_deep["Market"] == low_margin["Market"] else
    "%d countries are loss-making in aggregate; %s has the lowest margin (%s)." % (
        len(losers), low_margin["Market"], m.fmt_pct(low_margin["Margin"])),
    implication="Market underperformance lines up with discount intensity rather than with market size or segment mix "
                "(association, not proof of causation).",
    action="Reprice the largest loss-making countries first instead of exiting them; market exit should only be "
           "considered for countries still loss-making after two quarters under the discount ceiling.",
)
