import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Title
st.title("📈 Geopolitical Tension Monitor")

# Tickers & Weights
tickers = {
    "GC=F": 0.25, "CL=F": 0.25, "LMT": 0.0667, "NOC": 0.0667, "RTX": 0.0667,
    "XOM": 0.05, "CVX": 0.05, "BP": 0.05, "ZIM": 0.05, "AMKBY": 0.05, "CMRE": 0.05
}

# Date range
end_date = datetime.today()
start_date = end_date - timedelta(days=365)

# Fetch data
data = yf.download(list(tickers.keys()), start=start_date, end=end_date)['Close']

# Handle MultiIndex
if isinstance(data.columns, pd.MultiIndex):
    data = data.copy()

# Calculate changes
returns = data.pct_change().fillna(0)
signal_strength = (returns * list(tickers.values())).sum(axis=1)
signal_percent = (signal_strength - signal_strength.min()) / (signal_strength.max() - signal_strength.min()) * 100

# Latest table
latest_df = pd.DataFrame({
    "Ticker": tickers.keys(),
    "Weight": tickers.values()
})
latest_df.index += 1

# Display table
st.subheader("📊 Latest Snapshot")
st.dataframe(latest_df)

# Plot chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=signal_percent.index, y=signal_percent, mode='lines', name='Tension Index'))
fig.add_hrect(y0=70, y1=100, fillcolor="red", opacity=0.1, line_width=0)  # High tension
fig.add_hrect(y0=40, y1=70, fillcolor="orange", opacity=0.1, line_width=0) # Medium
fig.add_hrect(y0=0, y1=40, fillcolor="green", opacity=0.1, line_width=0)   # Low
fig.update_layout(title="Geopolitical Tension Index", xaxis_title="Date", yaxis_title="Index (%)")

st.plotly_chart(fig, use_container_width=True)
