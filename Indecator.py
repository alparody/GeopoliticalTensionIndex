import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")
st.title("Geopolitical Tension Index (0–100 Scale)")

# -------------------------------
# Sidebar: Date range and restore
# -------------------------------
st.sidebar.header("📅 Date Selection")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())

if st.sidebar.button("Restore Default Dates"):
    start_date = date.today() - pd.Timedelta(days=365)
    end_date = date.today()

# -------------------------------
# Sidebar: Chart options
# -------------------------------
chart_type = st.sidebar.selectbox("Chart Type", ["Line", "Bar"])
st.sidebar.header("📊 Show/Hide Additional Indices")
show_SPY = st.sidebar.checkbox("SPY", value=True)
show_SP_Global = st.sidebar.checkbox("S&P Global", value=True)
show_MSCI = st.sidebar.checkbox("MSCI World", value=True)
show_VIX = st.sidebar.checkbox("VIX", value=True)
show_MOVE = st.sidebar.checkbox("MOVE Index", value=True)
show_GoldVol = st.sidebar.checkbox("Gold Volatility", value=True)

# -------------------------------
# Load stock weights (editable)
# -------------------------------
weights_df = pd.read_csv("stocks_weights.csv")
weights_df["full_name"] = weights_df["symbol"]  # placeholder, can add descriptive names

st.subheader("Adjust Weights and Sign")
weights_df = st.data_editor(weights_df, num_rows="dynamic")

if st.button("Restore Default Weights"):
    weights_df = pd.read_csv("stocks_weights.csv")
    weights_df["full_name"] = weights_df["symbol"]

# -------------------------------
# Fetch market data
# -------------------------------
symbols = weights_df["symbol"].tolist()
with st.spinner("Fetching market data…"):
    data = yf.download(symbols, start=start_date, end=end_date, auto_adjust=True)["Close"].dropna(how="all", axis=1)

if data.empty:
    st.error("No price data returned for the selected period.")
    st.stop()

# -------------------------------
# Compute returns and cumulative
# -------------------------------
returns = data.pct_change().dropna(how="all")
# z-score normalization
z_returns = (returns - returns.mean()) / returns.std()

# Weighted sum with sign
total_weight = weights_df["weight"].sum()
weighted = pd.DataFrame(index=z_returns.index)
for _, row in weights_df.iterrows():
    sign = 1 if int(row["positive"]) == 1 else -1
    if row["symbol"] in z_returns.columns:
        weighted[row["symbol"]] = z_returns[row["symbol"]] * (row["weight"] / total_weight) * sign

# EWMA smoothing
weighted = weighted.ewm(span=10).mean()
index_series = weighted.sum(axis=1).cumsum()

# Scale 0-100
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v) / (max_v - min_v) * 100 if max_v != min_v else pd.Series(50.0, index=index_series.index)

# -------------------------------
# Prepare plot dataframe
# -------------------------------
plot_df = pd.DataFrame({"GTI": index_pct})
if show_SPY and "SPY" in returns.columns: plot_df["SPY"] = returns["SPY"].cumsum()
if show_SP_Global and "^GSPC" in returns.columns: plot_df["S&P Global"] = returns["^GSPC"].cumsum()
if show_MSCI and "EEM" in returns.columns: plot_df["MSCI World"] = returns["EEM"].cumsum()
if show_VIX and "^VIX" in returns.columns: plot_df["VIX"] = returns["^VIX"].cumsum()
if show_MOVE and "MOVE" in returns.columns: plot_df["MOVE Index"] = returns["MOVE"].cumsum()
if show_GoldVol and "GC=F" in returns.columns: plot_df["Gold Volatility"] = returns["GC=F"].cumsum()

# -------------------------------
# Plot
# -------------------------------
st.subheader("Index Chart")
if chart_type == "Line":
    st.line_chart(plot_df)
else:
    st.bar_chart(plot_df)

# -------------------------------
# Show editable weights table below the chart
# -------------------------------
st.subheader("Stock Weights Table")
st.dataframe(weights_df)

# -------------------------------
# Performance metrics
# -------------------------------
st.subheader("Performance Metrics")
metrics = {
    "Final Index Value": float(index_pct.iloc[-1]),
    "Index Volatility": float(returns.sum(axis=1).std()),
    "Sharpe-like Ratio": float(returns.sum(axis=1).mean()/returns.sum(axis=1).std())
}
st.json(metrics)
