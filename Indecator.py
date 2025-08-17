import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date
import plotly.express as px

st.sidebar.title("🔧 Options")

# --- Choose chart type ---
chart_type = st.sidebar.selectbox("Select chart type", ["Line", "Bar"])

# --- Date inputs ---
st.sidebar.subheader("Select Date Range")
start_date = st.sidebar.date_input("From Date", date.today() - pd.Timedelta(days=365))
end_date = st.sidebar.date_input("To Date", date.today())
if st.sidebar.button("Today"):
    end_date = date.today()

st.set_page_config(page_title="Political Tension Index", layout="wide")
st.title("Political Tension Index (0–100 Scale)")

# --- Load CSV ---
csv_url = "https://raw.githubusercontent.com/alparody/GeopoliticalTensionIndex/refs/heads/main/stocks_weights.csv"
df = pd.read_csv(csv_url)
df["weight"] = df["weight"].astype(float)

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

# --- Weighted returns (sign-adjusted, normalized) ---
total_weight = df["weight"].sum()
weighted = pd.DataFrame(index=returns.index)
for _, row in df.iterrows():
    sign = 1 if int(row["positive"]) == 1 else -1
    weighted[row["symbol"]] = returns[row["symbol"]] * (row["weight"] / total_weight) * sign

# --- Build cumulative index then scale to 0–100 ---
index_series = weighted.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v) / (max_v - min_v) * 100.0 if max_v != min_v else pd.Series(50.0, index=index_series.index)

# --- Today's index value ---
today_pct = float(index_pct.iloc[-1])
color = "green" if today_pct >= 70 else "orange" if today_pct >= 40 else "red"

st.markdown(f"### Today's Index: **{today_pct:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# --- Charts ---
if chart_type == "Line":
    st.line_chart(index_pct, height=280)
else:  # Bar
    st.bar_chart(index_pct, height=280)

# --- Diagnostics ---
with st.expander("Data diagnostics"):
    if missing:
        st.warning(
            f"Missing data for {len(missing)} symbol(s): {', '.join(missing)}. "
            "They were excluded from the index."
        )
    else:
        st.write("All symbols fetched successfully.")

# --- Download button ---
st.download_button(
    label="Download Index Data (0–100)",
    data=index_pct.to_csv().encode("utf-8"),
    file_name="geopolitical_index.csv",
    mime="text/csv",
)
