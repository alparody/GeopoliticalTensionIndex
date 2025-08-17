import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Political Tension Index", layout="wide")
st.title("Political Tension Index (0–100 Scale)")

# --- Sidebar: التاريخ ---
st.sidebar.header("🔧 Analysis Settings")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())
if st.sidebar.button("Restore Default Dates"):
    start_date = date.today() - pd.Timedelta(days=365)
    end_date = date.today()

# --- Load weights CSV ---
weights_url = "https://raw.githubusercontent.com/alparody/GeopoliticalTensionIndex/main/stocks_weights.csv"
weights_df = pd.read_csv(weights_url)
weights_df["weight"] = weights_df["weight"].astype(float)
weights_df["positive"] = weights_df["positive"].astype(int)

# --- Sidebar: مؤشرات إضافية ---
st.sidebar.header("📊 Optional Indicators (checked = visible)")
show_vix = st.sidebar.checkbox("VIX", value=True)
show_move = st.sidebar.checkbox("MOVE Index", value=True)
show_gold_vol = st.sidebar.checkbox("Gold Volatility", value=True)

# --- Fetch market data ---
@st.cache_data(show_spinner=False)
def get_data(symbols, start, end):
    return yf.download(
        symbols,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )["Close"].dropna(how="all", axis=1)

with st.spinner("Fetching market data…"):
    data = get_data(weights_df["symbol"].tolist(), start_date, end_date)

if data is None or data.empty:
    st.error("No price data returned for the selected period.")
    st.stop()

# --- Compute daily returns ---
returns = data.pct_change(fill_method=None).dropna(how="all")

# --- Filter available symbols ---
available = [s for s in weights_df["symbol"] if s in returns.columns]
weights_df = weights_df[weights_df["symbol"].isin(available)].copy()
returns = returns[available]

# --- Compute weighted GTI ---
total_weight = weights_df["weight"].sum()
weighted = pd.DataFrame(index=returns.index)
for _, row in weights_df.iterrows():
    sign = 1 if int(row["positive"]) == 1 else -1
    weighted[row["symbol"]] = returns[row["symbol"]] * (row["weight"] / total_weight) * sign

# --- EWMA smoothing & z-score normalization ---
smoothed = weighted.ewm(span=5).mean()
zscore_norm = (smoothed - smoothed.mean()) / smoothed.std()

index_series = zscore_norm.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v) / (max_v - min_v) * 100.0
today_pct = float(index_pct.iloc[-1])
color = "green" if today_pct >= 70 else "orange" if today_pct >= 40 else "red"

# --- Prepare optional indicators ---
optional_indicators = pd.DataFrame(index=returns.index)
if show_vix and "^VIX" in returns.columns:
    optional_indicators["VIX"] = returns["^VIX"].cumsum()
if show_move and "MOVE_INDEX_SYMBOL" in returns.columns:
    optional_indicators["MOVE"] = returns["MOVE_INDEX_SYMBOL"].cumsum()
if show_gold_vol and "GC=F" in returns.columns:
    optional_indicators["Gold Volatility"] = returns["GC=F"].cumsum()

# --- Merge GTI + optional for plotting ---
plot_df = pd.concat([index_pct.rename("GTI"), optional_indicators], axis=1)

# --- Chart type ---
chart_type = st.selectbox("Select chart type", ["Line", "Bar"])
if chart_type == "Line":
    st.line_chart(plot_df, height=300)
else:
    fig = px.bar(plot_df, labels={"value":"Index","index":"Date"}, title="Political Tension Index + Optional Indicators")
    st.plotly_chart(fig, use_container_width=True)

st.markdown(f"### Today's Index: **{today_pct:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# --- Table: adjustable weights & sign (تحت الرسم البياني فقط) ---
st.markdown("### Adjust weights & sign (Positive = 1, Negative = 0)")
weights_df = st.data_editor(weights_df, key="weights_editor", use_container_width=True)

# --- Optional: download index ---
st.download_button(
    label="Download GTI (0–100)",
    data=index_pct.to_csv().encode("utf-8"),
    file_name="geopolitical_index.csv",
    mime="text/csv",
)
