import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date
import plotly.express as px
import numpy as np
from scipy.stats import zscore

st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")
st.title("Political Tension Index (0–100 Scale)")

# --- Sidebar: Date Selection ---
st.sidebar.header("Date Range")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())
if st.sidebar.button("Restore Today"):
    start_date = date.today() - pd.Timedelta(days=365)
    end_date = date.today()

# --- Sidebar: Optional Indicators ---
st.sidebar.header("Optional Indicators")
show_vix = st.sidebar.checkbox("Show VIX", value=True)
show_move = st.sidebar.checkbox("Show MOVE Index", value=True)
show_gold_vol = st.sidebar.checkbox("Show Gold Volatility", value=True)

# --- Sidebar: Chart type ---
chart_type = st.sidebar.radio("Chart Type", ["Line", "Bar"])

# --- Load stock weights ---
weights_df = pd.read_csv("stocks_weights.csv")
weights_df["weight"] = weights_df["weight"].astype(float)
weights_df_default = weights_df.copy()

# --- Editable table for weights ---
st.sidebar.header("Adjust Weights/Sign")
edited_weights = st.experimental_data_editor(weights_df, num_rows="dynamic")

if st.sidebar.button("Restore Default Weights"):
    edited_weights = weights_df_default.copy()

# --- Fetch data from Yahoo ---
@st.cache_data(show_spinner=False)
def get_data(symbols, start, end):
    return yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)["Close"].dropna(how="all", axis=1)

data = get_data(edited_weights["symbol"].tolist(), start_date, end_date)

if data.empty:
    st.error("No data returned for selected period.")
    st.stop()

# --- Compute daily returns ---
returns = data.pct_change().dropna(how="all")

# --- Weighted returns using EWMA & z-score ---
total_weight = edited_weights["weight"].sum()
weighted = pd.DataFrame(index=returns.index)
for _, row in edited_weights.iterrows():
    symbol = row["symbol"]
    if symbol in returns.columns:
        sign = 1 if int(row["positive"]) == 1 else -1
        daily = returns[symbol].ewm(span=5).mean()  # EWMA
        weighted[symbol] = zscore(daily) * (row["weight"] / total_weight) * sign

# --- Cumulative index and scale 0–100 ---
index_series = weighted.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()
if max_v == min_v:
    index_pct = pd.Series(50.0, index=index_series.index)
else:
    index_pct = (index_series - min_v) / (max_v - min_v) * 100.0

# --- Optional indicators ---
optional_indicators = pd.DataFrame(index=returns.index)
if show_vix and "^VIX" in returns.columns:
    optional_indicators["VIX"] = returns["^VIX"].ewm(span=5).mean().cumsum()
if show_move and "MOVE" in returns.columns:
    optional_indicators["MOVE"] = returns["MOVE"].ewm(span=5).mean().cumsum()
if show_gold_vol and "GC=F" in returns.columns:
    optional_indicators["Gold Volatility"] = returns["GC=F"].rolling(5).std().fillna(0).cumsum()

# --- Plotting ---
plot_df = pd.concat([index_pct, optional_indicators], axis=1)
if chart_type == "Line":
    st.line_chart(plot_df, height=300)
else:
    st.bar_chart(plot_df, height=300)

# --- Show Today's Index ---
today_pct = float(index_pct.iloc[-1])
color = "green" if today_pct >= 70 else "orange" if today_pct >= 40 else "red"
st.markdown(f"### Today's Index: **{today_pct:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# --- Table of edited weights below chart ---
st.subheader("Stocks Weights & Signs")
st.dataframe(edited_weights, use_container_width=True)
