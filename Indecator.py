import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -------------------
# User-configurable parameters
# -------------------
TICKERS = {
    'GC=F': 0.25,   # Gold
    'CL=F': 0.25,   # Oil
    'LMT': 0.0667,  # Lockheed Martin
    'NOC': 0.0667,  # Northrop Grumman
    'RTX': 0.0667,  # Raytheon
    'XOM': 0.05,    # Exxon Mobil
    'CVX': 0.05,    # Chevron
    'BP': 0.05,     # BP
    'ZIM': 0.05,    # ZIM Shipping
    'AMKBY': 0.05,  # Maersk
    'CMRE': 0.05    # Costamare
}

PERIOD_OPTIONS = {
    "Last Day": "1d",
    "Last Week": "7d",
    "Last Month": "30d",
    "Last 6 Months": "180d",
    "Last Year": "365d"
}

ALERT_THRESHOLD = 0.6
SAFE_THRESHOLD = 0.3

# -------------------
# Streamlit UI
# -------------------
st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")

st.title("🌍 Geopolitical Tension Index")
st.markdown("This dashboard shows market-based signals for geopolitical tension.")

period_choice = st.sidebar.selectbox("Select Period", list(PERIOD_OPTIONS.keys()), index=4)
period_days = int(PERIOD_OPTIONS[period_choice].replace("d", ""))

end_date = datetime.today()
start_date = end_date - timedelta(days=period_days)

# -------------------
# Data Fetching
# -------------------
st.info(f"Fetching data from {start_date.date()} to {end_date.date()} ...")

data_all = yf.download(list(TICKERS.keys()), start=start_date, end=end_date, interval="1d")

if isinstance(data_all.columns, pd.MultiIndex):
    close_df = data_all['Close'].copy()
else:
    close_df = data_all[['Close']].copy()

# -------------------
# Calculations
# -------------------
returns = close_df.pct_change().dropna()

signals = []
for ticker, weight in TICKERS.items():
    if ticker in returns.columns:
        avg_change = returns[ticker].mean()
        signal_strength = 1 if avg_change > 0 else 0  # Simplified rule: positive avg = tension signal
        signals.append({
            "Ticker": ticker,
            "AvgChange(%)": avg_change * 100,
            "SignalStrength": signal_strength,
            "Weight": weight
        })

signals_df = pd.DataFrame(signals)
weighted_score = (signals_df["SignalStrength"] * signals_df["Weight"]).sum()

# -------------------
# Status Message
# -------------------
if weighted_score >= ALERT_THRESHOLD:
    st.error(f"🚨 High Tension Alert! Index = {weighted_score:.2%}")
elif weighted_score <= SAFE_THRESHOLD:
    st.success(f"✅ Situation appears calm. Index = {weighted_score:.2%}")
else:
    st.warning(f"⚠️ Moderate Tension. Index = {weighted_score:.2%}")

# -------------------
# Table
# -------------------
st.subheader("📊 Ticker Signals")
st.dataframe(signals_df.style.format({"AvgChange(%)": "{:.3f}", "Weight": "{:.4f}"}))

# -------------------
# Plotly Chart
# -------------------
fig = go.Figure()
for col in close_df.columns:
    fig.add_trace(go.Scatter(x=close_df.index, y=close_df[col], mode='lines', name=col))

fig.update_layout(
    title="Price Trends of Selected Tickers",
    xaxis_title="Date",
    yaxis_title="Price",
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

st.caption("Data source: Yahoo Finance | Analysis by Geopolitical Tension Index")
