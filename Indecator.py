import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date

st.sidebar.title("🔧 Testing Tools")

st.set_page_config(page_title="Political Tension Index", layout="wide")
st.title("Political Tension Index (0–100 Scale)")

# --- Load CSV weights ---
csv_url = "https://raw.githubusercontent.com/alparody/GeopoliticalTensionIndex/refs/heads/main/stocks_weights.csv"
df = pd.read_csv(csv_url)
df["weight"] = df["weight"].astype(float)

# --- Date inputs ---
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())

# --- Cache data fetch ---
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
    data = get_data(df["symbol"].tolist(), start_date, end_date)

if data is None or data.empty:
    st.error("No price data was returned for the selected period.")
    st.stop()

# --- Compute returns ---
returns = data.pct_change(fill_method=None).dropna(how="all")

# --- Filter missing symbols ---
available = [s for s in df["symbol"] if s in returns.columns]
missing = [s for s in df["symbol"] if s not in returns.columns]
df = df[df["symbol"].isin(available)].copy()
returns = returns[available]

if df.empty:
    st.error("All symbols are missing data after filtering. Please check your CSV.")
    st.stop()

# --- Weighted returns (sign-adjusted, normalized) ---
total_weight = df["weight"].sum()
weighted = pd.DataFrame(index=returns.index)

for _, row in df.iterrows():
    sign = 1 if int(row["positive"]) == 1 else -1
    weighted[row["symbol"]] = returns[row["symbol"]] * (row["weight"] / total_weight) * sign

# --- Build cumulative index then scale to 0–100 ---
index_series = weighted.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()

if max_v == min_v:
    index_pct = pd.Series(50.0, index=index_series.index)
else:
    index_pct = (index_series - min_v) / (max_v - min_v) * 100.0

# --- Today's index value ---
today_pct = float(index_pct.iloc[-1])
color = "green" if today_pct >= 70 else "orange" if today_pct >= 40 else "red"

st.markdown(f"### Today's Index: **{today_pct:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# --- Download button ---
st.download_button(
    label="Download Index Data (0–100)",
    data=index_pct.to_csv().encode("utf-8"),
    file_name="geopolitical_index.csv",
    mime="text/csv",
)
