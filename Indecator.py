import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date

st.set_page_config(page_title="Political Tension Index", layout="wide")
st.title("Political Tension Index (0–100 Scale)")

# Read CSV from GitHub repository (replace URL with actual raw link)
csv_url = "https://raw.githubusercontent.com/alparody/GeopoliticalTensionIndex/refs/heads/main/stocks_weights.csv"
df = pd.read_csv(csv_url)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())

# Fetch data
data = yf.download(df["symbol"].tolist(), start=start_date, end=end_date)["Close"].dropna(how="all", axis=1)
returns = data.pct_change().dropna()

# Weighted returns sign-adjusted
weighted = pd.DataFrame()
for _, row in df.iterrows():
    s = row["symbol"]
    if s in returns.columns:
        sign = 1 if row["positive"] == 1 else -1
        weighted[s] = returns[s] * row["weight"] * sign

# Compute index (cumulative), then scale 0–100
index_series = weighted.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v) / (max_v - min_v) * 100

today_pct = index_pct.iloc[-1]
color = "green" if today_pct >= 70 else "orange" if today_pct >= 40 else "red"

st.markdown(f"### Today's Index: **{today_pct:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# Plot
st.line_chart(index_pct)
