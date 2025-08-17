import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Interactive GTI Editor", layout="wide")
st.title("Interactive Geopolitical Tension Index Editor")

# --- Load default CSV ---
csv_url = "https://raw.githubusercontent.com/alparody/GeopoliticalTensionIndex/refs/heads/main/stocks_weights.csv"
default_df = pd.read_csv(csv_url)
default_df["weight"] = default_df["weight"].astype(float)
default_df["positive"] = default_df["positive"].astype(int)

# --- Editable data editor ---
st.subheader("Edit Weights and Signs")
edited_df = st.data_editor(default_df, num_rows="dynamic")

# --- Date inputs ---
col1, col2, col3 = st.columns([2,2,1])
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())
with col3:
    if st.button("Today"):
        start_date = date.today() - pd.Timedelta(days=365)
        end_date = date.today()

# --- Fetch market data ---
@st.cache_data(show_spinner=False)
def get_data(symbols, start, end):
    data = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)
    return data["Close"].dropna(how="all", axis=1)

symbols = edited_df["symbol"].tolist()
with st.spinner("Fetching market data…"):
    data = get_data(symbols, start_date, end_date)

if data is None or data.empty:
    st.error("No price data returned for selected period.")
    st.stop()

# --- Compute weighted returns ---
returns = data.pct_change().dropna(how="all")
total_weight = edited_df["weight"].sum()
weighted = pd.DataFrame(index=returns.index)
for _, row in edited_df.iterrows():
    sign = 1 if row["positive"] == 1 else -1
    weighted[row["symbol"]] = returns[row["symbol"]] * (row["weight"]/total_weight) * sign

# --- Build cumulative index ---
index_series = weighted.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v) / (max_v - min_v) * 100 if max_v != min_v else pd.Series(50.0, index=index_series.index)

# --- Display result ---
st.subheader("Cumulative Index (0–100)")
st.line_chart(index_pct, height=300)

st.markdown(f"### Today's Index: **{index_pct.iloc[-1]:.2f}%**")
