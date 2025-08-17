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
df["weight"] = df["weight"].astype(float)

# --- Symbol aliases for robustness ---
SYMBOL_ALIASES = {
    "VIX": "^VIX",          # CBOE Volatility Index
    "^MSCIEF": "EEM",       # MSCI EM -> iShares EM ETF
    "DE10Y.BUND": "BNDX",   # German Bund proxy -> Intl Bonds (USD-hedged)
}
df["fetch_symbol"] = df["symbol"].replace(SYMBOL_ALIASES)

# Date inputs
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())

# Cache data fetch
@st.cache_data(show_spinner=False)
def get_data(symbols, start, end):
    # auto_adjust=True returns adjusted Close in "Close" column (no Adj Close column)
    return yf.download(
        symbols,
        start=start,
        end=end,
        auto_adjust=True,
        group_by="column",
        progress=False,
    )["Close"].dropna(how="all", axis=1)

with st.spinner("Fetching market data…"):
    data = get_data(df["fetch_symbol"].tolist(), start_date, end_date)

if data is None or data.empty:
    st.error("No price data was returned for the selected period.")
    st.stop()

# Compute returns (avoid future warning)
returns = data.pct_change(fill_method=None).dropna(how="all")

# Map fetched symbols back to original symbols for display
fetch_to_original = dict(zip(df["fetch_symbol"], df["symbol"]))

# Keep only symbols that have data
available_fetch = [s for s in df["fetch_symbol"] if s in returns.columns]
missing_fetch = [s for s in df["fetch_symbol"] if s not in returns.columns]

df = df[df["fetch_symbol"].isin(available_fetch)].copy()
if df.empty:
    st.error("All symbols are missing data after filtering. Please check your CSV.")
    st.stop()

# Rename returns columns to original symbols for contributions/viz
returns = returns[available_fetch].rename(columns=fetch_to_original)

# Weighted returns (sign-adjusted) + normalized by total weight
total_weight = df["weight"].sum()
weighted = pd.DataFrame(index=returns.index)

for _, row in df.iterrows():
    s_orig = row["symbol"]
    sign = 1 if int(row["positive"]) == 1 else -1
    weighted[s_orig] = returns[s_orig] * (row["weight"] / total_weight) * sign

# Build cumulative index then scale to 0–100 safely
index_series = weighted.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()
if max_v == min_v:
    index_pct = pd.Series(50.0, index=index_series.index)  # flat series
else:
    index_pct = (index_series - min_v) / (max_v - min_v) * 100.0

# Today's index value
today_pct = float(index_pct.iloc[-1])
color = "green" if today_pct >= 70 else "orange" if today_pct >= 40 else "red"

st.markdown(f"### Today's Index: **{today_pct:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# Charts
st.line_chart(index_pct, height=280)

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

# Diagnostics: show mappings and dropped symbols
with st.expander("Data diagnostics"):
    # Show which symbols were mapped to alternatives
    mapped = df[df["symbol"] != df["fetch_symbol"]][["symbol", "fetch_symbol"]]
    if not mapped.empty:
        st.write("**Aliased symbols (replacements used to fetch data):**")
        st.dataframe(mapped.reset_index(drop=True), use_container_width=True)
    else:
        st.write("No symbol aliases were needed.")

    # Show symbols that were missing from returns
    if missing_fetch:
        # Convert fetch -> original for readability
        missing_original = [fetch_to_original.get(s, s) for s in missing_fetch]
        st.warning(
            f"Missing data for {len(missing_original)} symbol(s): {', '.join(missing_original)}. "
            "They were excluded from the index."
        )

# Download button for index data
st.download_button(
    label="Download Index Data (0–100)",
    data=index_pct.to_csv().encode("utf-8"),
    file_name="geopolitical_index.csv",
    mime="text/csv",
)
