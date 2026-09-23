"""Global Superstore executive dashboard - entry point.

Run with:  streamlit run app.py
"""

import streamlit as st

from utils.data_loader import FILTER_KEYS, filter_options, init_filter_state, load_data, reset_filters

st.set_page_config(
    page_title="Global Superstore | Executive dashboard",
    page_icon=":material/insights:",
    layout="wide",
    initial_sidebar_state="expanded",
)

df = load_data()
init_filter_state(df)
opts = filter_options(df)

page = st.navigation(
    {
        "Performance": [
            st.Page("app_pages/overview.py", title="Executive overview", icon=":material/dashboard:", default=True),
            st.Page("app_pages/trends.py", title="Trends", icon=":material/trending_up:"),
            st.Page("app_pages/markets.py", title="Markets and segments", icon=":material/public:"),
            st.Page("app_pages/products.py", title="Products", icon=":material/inventory_2:"),
        ],
        "Diagnosis": [
            st.Page("app_pages/root_cause.py", title="Profitability root cause", icon=":material/troubleshoot:"),
            st.Page("app_pages/strategy.py", title="Strategic insights", icon=":material/flag:"),
        ],
        "Reference": [
            st.Page("app_pages/data_quality.py", title="Data and methodology", icon=":material/fact_check:"),
        ],
    },
    position="top",
)

with st.sidebar:
    st.markdown("### :material/tune: Filters")
    st.slider("Order year", min_value=opts["years"][0], max_value=opts["years"][-1], step=1,
              key=FILTER_KEYS["years"])
    st.multiselect("Market", opts["markets"], key=FILTER_KEYS["markets"], placeholder="All markets")
    st.multiselect("Segment", opts["segments"], key=FILTER_KEYS["segments"], placeholder="All segments")
    st.multiselect("Category", opts["categories"], key=FILTER_KEYS["categories"], placeholder="All categories")
    st.button("Reset filters", icon=":material/restart_alt:", on_click=reset_filters, args=(df,),
              width="stretch")
    st.caption("An empty selection means all. KPI cards compare the last selected year with the year before it.")
    st.divider()
    st.caption(
        "Source: Global Superstore order lines, %s - %s (%s lines, %d countries). "
        "Every figure is computed live from the dataset; nothing is estimated or invented."
        % (df["Order Date"].min().strftime("%b %Y"), df["Order Date"].max().strftime("%b %Y"),
           "{:,}".format(len(df)), df["Country"].nunique())
    )

page.run()
