import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date
import plotly.express as px

st.set_page_config(page_title="Political Tension Index", layout="wide")
st.title("Political Tension Index (0–100 Scale)")

# --- Load CSV ---
csv_url = "https://raw.githubusercontent.com/alparody/GeopoliticalTensionIndex/refs/heads/main/stocks_weights.csv"
df = pd.read_csv(csv_url)
df["weight"] = df["weight"].astype(float)
df["positive"] = df["positive"].astype(int)

# --- Date inputs ---
st.sidebar.header("Date Selection")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())
if st.sidebar.button("Today"):
    start_date = date.today() - pd.Timedelta(days=365)
    end_date = date.today()

# --- Editable table for weights/positivity ---
st.sidebar.header("Edit Symbols")
edited_df = st.sidebar.data_editor(df, num_rows="dynamic")

# --- Cache data fetch ---
@st.cache_data(show_spinner=False)
def get_data(symbols, start, end):
    data = yf.download(
        symbols,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )
    return data["Close"].dropna(how="all", axis=1)

with st.spinner("Fetching market data…"):
    raw_data = get_data(edited_df["symbol"].tolist(), start_date, end_date)

if raw_data is None or raw_data.empty:
    st.error("No price data returned for the selected period.")
    st.stop()

# --- Compute returns ---
returns = raw_data.pct_change().dropna(how="all")

# --- Filter available symbols ---
available_symbols = [s for s in edited_df["symbol"] if s in returns.columns]
missing_symbols = [s for s in edited_df["symbol"] if s not in returns.columns]

if missing_symbols:
    st.warning(f"Missing data for symbols: {', '.join(missing_symbols)}. They will be excluded.")

edited_df = edited_df[edited_df["symbol"].isin(available_symbols)]
returns = returns[available_symbols]

# --- Weighted returns ---
total_weight = edited_df["weight"].sum()
weighted = pd.DataFrame(index=returns.index)
for _, row in edited_df.iterrows():
    symbol = row["symbol"]
    sign = 1 if row["positive"] == 1 else -1
    weighted[symbol] = returns[symbol] * (row["weight"] / total_weight) * sign

# --- Cumulative index ---
index_series = weighted.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v) / (max_v - min_v) * 100 if max_v != min_v else pd.Series(50.0, index=index_series.index)

# --- Today's index value ---
today_pct = float(index_pct.iloc[-1])
color = "green" if today_pct >= 70 else "orange" if today_pct >= 40 else "red"
st.markdown(f"### Today's Index: **{today_pct:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# --- Line chart ---
st.line_chart(index_pct, height=280)

# --- Contributions ---
contrib = weighted.iloc[-1].sort_values()
fig = px.bar(
    contrib,
    title="Today's Contributions",
    orientation="h",
    labels={"value": "Contribution", "index": "Symbol"},
    color=contrib.values,
    color_continuous_scale="RdYlGn",
)
st.plotly_chart(fig, use_container_width=True)

# --- Download button ---
st.download_button(
    label="Download Index Data (0–100)",
    data=index_pct.to_csv().encode("utf-8"),
    file_name="geopolitical_index.csv",
    mime="text/csv",
)
