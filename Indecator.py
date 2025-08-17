import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date
import plotly.express as px

st.set_page_config(page_title="Political Tension Index", layout="wide")
st.title("Political Tension Index (0–100 Scale)")

# Read CSV from GitHub repository (replace URL with actual raw link)
csv_url = "https://raw.githubusercontent.com/alparody/GeopoliticalTensionIndex/refs/heads/main/stocks_weights.csv"
df = pd.read_csv(csv_url)
df["weight"] = df["weight"].astype(float)  # ensure float

# Date inputs
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())

# Cache data fetch
@st.cache_data
def get_data(symbols, start, end):
    return yf.download(symbols, start=start, end=end)["Close"].dropna(how="all", axis=1)

data = get_data(df["symbol"].tolist(), start_date, end_date)

# Compute returns
returns = data.pct_change().dropna()

# Keep only symbols that have data
available_symbols = [s for s in df["symbol"] if s in returns.columns]
df = df[df["symbol"].isin(available_symbols)]

# Weighted returns sign-adjusted + normalized
total_weight = df["weight"].sum()
weighted = pd.DataFrame()
for _, row in df.iterrows():
    s = row["symbol"]
    sign = 1 if row["positive"] == 1 else -1
    weighted[s] = returns[s] * row["weight"] / total_weight * sign

# Compute index (cumulative), then scale 0–100
index_series = weighted.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v) / (max_v - min_v) * 100

# Today's index value
today_pct = index_pct.iloc[-1]
color = "green" if today_pct >= 70 else "orange" if today_pct >= 40 else "red"

st.markdown(f"### Today's Index: **{today_pct:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# Plot index over time
st.line_chart(index_pct)

# Contribution breakdown (last day)
contrib = weighted.iloc[-1].sort_values()
fig = px.bar(contrib, title="Today's Contributions", orientation="h",
             labels={"value": "Contribution", "index": "Symbol"},
             color=contrib.values, color_continuous_scale="RdYlGn")
st.plotly_chart(fig, use_container_width=True)

# Download button for index data
st.download_button(
    label="Download Index Data",
    data=index_pct.to_csv().encode('utf-8'),
    file_name="geopolitical_index.csv",
    mime="text/csv",
)
