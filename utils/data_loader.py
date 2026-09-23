"""Load, clean, validate and filter the Global Superstore order-line data."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "Global_Superstore2.csv"

DATE_COLS = ["Order Date", "Ship Date"]
NUMERIC_COLS = ["Sales", "Quantity", "Discount", "Profit", "Shipping Cost", "Postal Code"]
TEXT_COLS = [
    "Order ID", "Ship Mode", "Customer ID", "Customer Name", "Segment", "City",
    "State", "Country", "Market", "Region", "Product ID", "Category",
    "Sub-Category", "Product Name", "Order Priority",
]

DEEP_DISCOUNT = 0.30
DISCOUNT_BINS = [-0.001, 0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 1.0]
DISCOUNT_LABELS = ["0%", "1-10%", "11-20%", "21-30%", "31-40%", "41-50%", ">50%"]

FILTER_KEYS = {
    "years": "f_years",
    "markets": "f_markets",
    "segments": "f_segments",
    "categories": "f_categories",
}


@st.cache_data(show_spinner="Loading order data...")
def load_raw(path: str = str(DATA_PATH)) -> pd.DataFrame:
    """Read the CSV exactly as delivered (latin-1 encoded)."""
    return pd.read_csv(path, encoding="latin-1")


@st.cache_data(show_spinner="Preparing data...")
def load_data(path: str = str(DATA_PATH)) -> pd.DataFrame:
    """Return the cleaned, enriched order-line table used by every page."""
    return clean_data(load_raw(path))


def clean_data(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for col in TEXT_COLS:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%d-%m-%Y", errors="coerce")

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.drop_duplicates()
    df = df.dropna(subset=["Order Date", "Sales", "Profit"])
    df = df[df["Sales"] > 0].copy()
    df["Discount"] = df["Discount"].fillna(0.0).clip(0.0, 1.0)

    df["Year"] = df["Order Date"].dt.year.astype(int)
    df["Quarter"] = df["Order Date"].dt.to_period("Q").dt.to_timestamp()
    df["Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
    df["Month Num"] = df["Order Date"].dt.month.astype(int)
    df["Order Key"] = df["Order ID"] + "|" + df["Order Date"].dt.strftime("%Y-%m-%d")
    df["Discount Band"] = pd.cut(
        df["Discount"], bins=DISCOUNT_BINS, labels=DISCOUNT_LABELS, ordered=True
    )
    df["Deep Discount"] = df["Discount"] > DEEP_DISCOUNT
    df["Line Margin"] = (df["Profit"] / df["Sales"]).replace([np.inf, -np.inf], np.nan)
    df["Is Loss"] = df["Profit"] < 0
    df["Ship Days"] = (df["Ship Date"] - df["Order Date"]).dt.days
    return df.reset_index(drop=True)


@st.cache_data
def quality_report(path: str = str(DATA_PATH)) -> dict:
    """Facts about the raw file and what cleaning changed."""
    raw = load_raw(path)
    clean = load_data(path)
    order_dates = pd.to_datetime(raw["Order Date"], format="%d-%m-%Y", errors="coerce")
    ship_dates = pd.to_datetime(raw["Ship Date"], format="%d-%m-%Y", errors="coerce")
    missing = raw.isna().sum()
    missing_tbl = pd.DataFrame({
        "Column": missing.index,
        "Missing values": missing.values,
        "Missing %": (missing.values / max(len(raw), 1)),
    })
    postal_missing = raw["Postal Code"].isna()
    postal_non_us = (raw.loc[postal_missing, "Country"] != "United States").mean() if postal_missing.any() else np.nan
    return {
        "raw_rows": len(raw),
        "raw_cols": raw.shape[1],
        "clean_rows": len(clean),
        "dropped_rows": len(raw) - len(clean),
        "duplicate_rows": int(raw.duplicated().sum()),
        "duplicate_row_ids": int(raw["Row ID"].duplicated().sum()),
        "invalid_dates": int(order_dates.isna().sum() + ship_dates.isna().sum()),
        "ship_before_order": int((ship_dates < order_dates).sum()),
        "date_min": order_dates.min(),
        "date_max": order_dates.max(),
        "missing_table": missing_tbl,
        "postal_missing_non_us_share": postal_non_us,
        "order_ids": int(raw["Order ID"].nunique()),
        "order_keys": int(clean["Order Key"].nunique()),
        "customer_ids": int(raw["Customer ID"].nunique()),
        "customer_names": int(raw["Customer Name"].nunique()),
        "product_ids": int(raw["Product ID"].nunique()),
        "product_names": int(raw["Product Name"].nunique()),
        "countries": int(raw["Country"].nunique()),
        "markets": int(raw["Market"].nunique()),
    }


DATA_DICTIONARY = [
    ("Row ID", "Identifier", "Unique id of one order line", "Row count, de-duplication check"),
    ("Order ID", "Identifier", "Order number (can repeat across dates)", "Order counts together with Order Date"),
    ("Order Date", "Time", "Date the order was placed", "Trends, YoY, CAGR, seasonality"),
    ("Ship Date", "Time", "Date the order shipped", "Fulfilment lead time"),
    ("Ship Mode", "Dimension", "Delivery service level", "Operational driver check"),
    ("Customer ID", "Identifier", "Customer account id (region-specific)", "Customer counts (with caveat)"),
    ("Customer Name", "Dimension", "Customer name", "Customer look-ups"),
    ("Segment", "Dimension", "Consumer, Corporate or Home Office", "Segment comparison"),
    ("City", "Geography", "Delivery city", "Local drill-down"),
    ("State", "Geography", "Delivery state or province", "Local drill-down"),
    ("Country", "Geography", "Delivery country (147)", "Country ranking, map"),
    ("Postal Code", "Geography", "Postal code, US rows only", "Not used (80% missing by design)"),
    ("Market", "Geography", "Commercial market (7)", "Market comparison, filter"),
    ("Region", "Geography", "Sales region (13)", "Regional drill-down"),
    ("Product ID", "Identifier", "SKU id (region-specific)", "Product counts"),
    ("Category", "Dimension", "Furniture, Office Supplies, Technology", "Portfolio mix, filter"),
    ("Sub-Category", "Dimension", "17 product families", "Product profitability"),
    ("Product Name", "Dimension", "Product description", "Pareto and loss-making products"),
    ("Sales", "Measure", "Net revenue of the line after discount (USD)", "Revenue KPIs"),
    ("Quantity", "Measure", "Units sold on the line", "Volume KPIs"),
    ("Discount", "Measure", "Discount rate applied (0 to 0.85)", "Pricing driver analysis"),
    ("Profit", "Measure", "Profit of the line (USD, can be negative)", "Profit and margin KPIs"),
    ("Shipping Cost", "Measure", "Freight cost of the line (USD)", "Context only; not deducted from Profit"),
    ("Order Priority", "Dimension", "Critical, High, Medium, Low", "Operational driver check"),
]

DERIVED_FIELDS = [
    ("Year / Quarter / Month", "Time", "Calendar buckets of Order Date", "Trend charts"),
    ("Order Key", "Identifier", "Order ID + Order Date", "Distinct order count"),
    ("Discount Band", "Dimension", "Discount grouped into 7 bands", "Root-cause analysis"),
    ("Deep Discount", "Flag", "Discount above 30%", "Loss driver KPI"),
    ("Line Margin", "Measure", "Profit / Sales per line", "Correlation with discount"),
    ("Is Loss", "Flag", "Profit below zero", "Share of loss-making lines"),
]


def data_dictionary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col, role, meaning, use in DATA_DICTIONARY:
        dtype = str(df[col].dtype) if col in df.columns else "n/a"
        rows.append({"Column": col, "Data type": dtype, "Role": role,
                     "Business meaning": meaning, "Potential use": use})
    return pd.DataFrame(rows)


def derived_dictionary() -> pd.DataFrame:
    return pd.DataFrame(DERIVED_FIELDS, columns=["Field", "Role", "Definition", "Used for"])


# ---------------------------------------------------------------- filters

def filter_options(df: pd.DataFrame) -> dict:
    return {
        "years": sorted(df["Year"].unique().tolist()),
        "markets": sorted(df["Market"].dropna().unique().tolist()),
        "segments": sorted(df["Segment"].dropna().unique().tolist()),
        "categories": sorted(df["Category"].dropna().unique().tolist()),
    }


def default_filters(df: pd.DataFrame) -> dict:
    years = filter_options(df)["years"]
    return {
        FILTER_KEYS["years"]: (years[0], years[-1]),
        FILTER_KEYS["markets"]: [],
        FILTER_KEYS["segments"]: [],
        FILTER_KEYS["categories"]: [],
    }


def init_filter_state(df: pd.DataFrame) -> None:
    for key, value in default_filters(df).items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_filters(df: pd.DataFrame) -> None:
    for key, value in default_filters(df).items():
        st.session_state[key] = value


@dataclass
class FilteredData:
    df: pd.DataFrame
    dims: pd.DataFrame
    start: int
    end: int
    label: str

    @property
    def n_years(self) -> int:
        return self.end - self.start + 1

    @property
    def empty(self) -> bool:
        return self.df.empty


def apply_filters(df, years, markets, segments, categories) -> FilteredData:
    """Empty multiselects mean 'all'. `dims` keeps every year for YoY comparisons."""
    mask = pd.Series(True, index=df.index)
    if markets:
        mask &= df["Market"].isin(markets)
    if segments:
        mask &= df["Segment"].isin(segments)
    if categories:
        mask &= df["Category"].isin(categories)
    dims = df[mask]
    if isinstance(years, (list, tuple)) and len(years) > 0:
        start, end = int(min(years)), int(max(years))
    elif years is not None and not isinstance(years, (list, tuple)):
        start = end = int(years)
    else:
        start, end = int(df["Year"].min()), int(df["Year"].max())
    filtered = dims[dims["Year"].between(start, end)]

    def part(values, noun):
        return ", ".join(values) if values else "All " + noun

    period = str(start) if start == end else "%d-%d" % (start, end)
    label = " | ".join([
        period, part(markets, "markets"), part(segments, "segments"),
        part(categories, "categories"), "{:,} order lines".format(len(filtered)),
    ])
    return FilteredData(df=filtered, dims=dims, start=start, end=end, label=label)


def get_filtered_data() -> FilteredData:
    df = load_data()
    init_filter_state(df)
    s = st.session_state
    return apply_filters(
        df,
        years=s[FILTER_KEYS["years"]],
        markets=s[FILTER_KEYS["markets"]],
        segments=s[FILTER_KEYS["segments"]],
        categories=s[FILTER_KEYS["categories"]],
    )
