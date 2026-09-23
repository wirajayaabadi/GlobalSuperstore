"""Reusable layout blocks: page header, KPI row, chart card, insight boxes."""

import streamlit as st

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}


def md(text: str) -> str:
    """Escape dollar signs so Streamlit markdown does not render them as LaTeX."""
    return str(text).replace("\\$", "$").replace("$", "\\$")


def page_header(section: str, headline: str, summary: str, fd) -> None:
    st.caption(section.upper())
    st.markdown("## " + md(headline))
    if summary:
        st.markdown(md(summary))
    st.caption(":material/filter_alt: " + md(fd.label))


def require_data(fd) -> None:
    if fd.empty:
        st.warning("No order lines match the current filters. Widen the selection or press "
                   "**Reset filters** in the sidebar.", icon=":material/filter_alt_off:")
        st.stop()


def section(title: str, caption: str = "") -> None:
    st.markdown("#### " + md(title))
    if caption:
        st.caption(md(caption))


def kpi_row(kpis: list, caption: str = "") -> None:
    with st.container(horizontal=True):
        for k in kpis:
            kwargs = {}
            if k.get("spark"):
                kwargs = {"chart_data": k["spark"], "chart_type": "line"}
            st.metric(k["label"], k["value"], k["delta"], delta_color=k.get("color", "normal"),
                      help=k.get("help"), border=True, **kwargs)
    if caption:
        st.caption(md(caption))


def chart_card(title: str, subtitle: str, fig, key: str, note: str = "") -> None:
    with st.container(border=True):
        st.markdown("**" + md(title) + "**")
        if subtitle:
            st.caption(md(subtitle))
        st.plotly_chart(fig, config=PLOTLY_CONFIG, key=key)
        if note:
            st.caption(md(note))


def insight_box(finding: str, implication: str, action: str, title: str = "Key insight") -> None:
    with st.container(border=True):
        st.markdown(":material/lightbulb: **" + md(title) + "**")
        st.markdown("**Finding.** " + md(finding))
        st.markdown("**Implication.** " + md(implication))
        st.markdown("**Action.** " + md(action))


def fir_card(number: int, title: str, fact: str, interpretation: str, recommendation: str) -> None:
    with st.container(border=True):
        st.markdown("**%d. %s**" % (number, md(title)))
        st.markdown(":blue-badge[Fact] " + md(fact))
        st.markdown(":gray-badge[Interpretation] " + md(interpretation))
        st.markdown(":green-badge[Recommendation] " + md(recommendation))
