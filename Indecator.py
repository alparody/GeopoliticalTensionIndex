import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import date
from scipy.stats import zscore
import base64
import requests

st.set_page_config(page_title="Political Tension Index", layout="wide")
st.title("Political Tension Index (0–100 Scale)")

# -----------------------------
# Load Weights CSV
# -----------------------------
@st.cache_data(show_spinner=False)
def load_weights():
    url = "https://raw.githubusercontent.com/alparody/GeopoliticalTensionIndex/refs/heads/main/stocks_weights.csv"
    df = pd.read_csv(url)
    df["weight"] = df["weight"].astype(float)
    return df

weights_df = load_weights()

# -----------------------------
# Adjust Weights and Signs
# -----------------------------
st.subheader("Adjust Weights and Sign")
weights_df = st.data_editor(weights_df, num_rows="dynamic")

# -----------------------------
# Restore Default Weights
# -----------------------------
if st.button("Restore Default Weights"):
    weights_df = load_weights()

# -----------------------------
# Date Inputs
# -----------------------------
st.sidebar.subheader("Select Date Range")
start_date = st.sidebar.date_input("From Date", date.today() - pd.Timedelta(days=365))
end_date = st.sidebar.date_input("To Date", date.today())
if st.sidebar.button("Restore Today"):
    start_date = date.today() - pd.Timedelta(days=365)
    end_date = date.today()

# -----------------------------
# Chart Type
# -----------------------------
chart_type = st.sidebar.selectbox("Chart Type", ["Line", "Bar"])

# -----------------------------
# Additional Indicators
# -----------------------------
st.sidebar.subheader("Additional Indicators")
show_vix = st.sidebar.checkbox("VIX", value=True)
show_move = st.sidebar.checkbox("MOVE Index", value=True)
show_gold_vol = st.sidebar.checkbox("Gold Volatility", value=True)

# -----------------------------
# Comparison Benchmarks
# -----------------------------
st.sidebar.subheader("Comparison Benchmarks")
show_spy = st.sidebar.checkbox("SPY", value=True)
show_gspc = st.sidebar.checkbox("S&P 500", value=True)
show_msciw = st.sidebar.checkbox("MSCI World", value=True)

# -----------------------------
# Symbols
# -----------------------------
additional_symbols = []
if show_vix: additional_symbols.append("^VIX")
if show_move: additional_symbols.append("^MOVE")
if show_gold_vol: additional_symbols.append("GVZ")

benchmark_symbols = []
if show_spy: benchmark_symbols.append("SPY")
if show_gspc: benchmark_symbols.append("^GSPC")
if show_msciw: benchmark_symbols.append("EEM")

all_symbols = weights_df["symbol"].tolist() + additional_symbols + benchmark_symbols

# -----------------------------
# Fetch Data
# -----------------------------
@st.cache_data(show_spinner=False)
def get_data(symbols, start, end):
    data = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    return data.dropna(how="all", axis=1)

data = get_data(all_symbols, start_date, end_date)
if data.empty:
    st.error("No price data returned for selected period.")
    st.stop()

# -----------------------------
# Calculate Returns & EWMA
# -----------------------------
returns = data.pct_change().dropna(how="all")
returns_ewma = returns.ewm(span=5).mean()

# -----------------------------
# Normalize each asset
# -----------------------------
returns_norm = returns_ewma.apply(zscore, nan_policy='omit')

# -----------------------------
# Weighted index calculation
# -----------------------------
available = [s for s in weights_df["symbol"] if s in returns_norm.columns]
weights_df = weights_df[weights_df["symbol"].isin(available)].copy()
total_weight = weights_df["weight"].sum()
weighted = pd.DataFrame(index=returns_norm.index)

for _, row in weights_df.iterrows():
    sign = 1 if int(row["positive"]) == 1 else -1
    weighted[row["symbol"]] = returns_norm[row["symbol"]] * (row["weight"] / total_weight) * sign

# -----------------------------
# Penalty factor for high drawdown
# -----------------------------
drawdown = weighted.sum(axis=1).cumsum().diff().fillna(0)
penalty = drawdown.apply(lambda x: x if x >= -0.05 else x * 2)
index_series = (weighted.sum(axis=1) + penalty).cumsum()

# -----------------------------
# Scale 0-100
# -----------------------------
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v) / (max_v - min_v) * 100 if max_v != min_v else pd.Series(50, index=index_series.index)

# -----------------------------
# Show Today's Index
# -----------------------------
today_pct = float(index_pct.iloc[-1])
color = "green" if today_pct >= 70 else "orange" if today_pct >= 40 else "red"
st.markdown(f"### Today's Index: **{today_pct:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# -----------------------------
# Chart
# -----------------------------
if chart_type == "Line":
    st.line_chart(index_pct)
else:
    fig_main = px.bar(index_pct, labels={"index":"Date","value":"Index"})
    st.plotly_chart(fig_main)

# -----------------------------
# Contributions Today
# -----------------------------
contrib = weighted.iloc[-1].sort_values()
fig2 = px.bar(contrib, orientation="h", color=contrib.values, color_continuous_scale="RdYlGn",
              title="Today's Contributions")
st.plotly_chart(fig2)

# -----------------------------
# Additional Indicators & Benchmarks
# -----------------------------
st.subheader("Additional Indicators / Benchmarks")
if additional_symbols + benchmark_symbols:
    st.line_chart(data[additional_symbols + benchmark_symbols].pct_change().cumsum())

# -----------------------------
# Performance Metrics
# -----------------------------
st.subheader("Performance Metrics")
metrics = []
for col in weights_df["symbol"]:
    r = returns[col].dropna()
    cum = (1+r).prod() - 1
    vol = r.std()
    sharpe = r.mean()/vol if vol>0 else 0
    corr_spy = r.corr(returns["SPY"].pct_change()) if "SPY" in returns.columns else None
    corr_vix = r.corr(returns["^VIX"].pct_change()) if "^VIX" in returns.columns else None
    metrics.append({"Symbol": col, "Cumulative": cum, "Volatility": vol, "Sharpe-like": sharpe,
                    "Corr with SPY": corr_spy, "Corr with VIX": corr_vix})

metrics_df = pd.DataFrame(metrics)
st.dataframe(metrics_df)

# -----------------------------
# Save updated weights to GitHub (requires secret)
# -----------------------------
def save_weights_github(df):
    token = st.secrets["GITHUB_PAT"]
    url = "https://raw.githubusercontent.com/alparody/GeopoliticalTensionIndex/refs/heads/main/stocks_weights.csv"
    content = df.to_csv(index=False)
    encoded = base64.b64encode(content.encode()).decode()
    r = requests.get(url, headers={"Authorization": f"token {token}"})
    if r.status_code == 200:
        sha = r.json()["sha"]
        msg = {"message":"Update weights from Streamlit", "content":encoded, "sha":sha}
        res = requests.put(url, headers={"Authorization": f"token {token}"}, json=msg)
        return res.status_code
    return None

if st.button("Save Weights to GitHub"):
    status = save_weights_github(weights_df)
    st.success(f"Saved! Response status: {status}")
