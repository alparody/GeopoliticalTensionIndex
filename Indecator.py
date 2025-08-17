# geopolitcal_indicator_app_final.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from datetime import date
import requests
from io import StringIO
import os

# =========================
# إعداد الصفحة
# =========================
st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")
st.title("Geopolitical Tension Index (0–100 Scale)")

# =========================
# Sidebar للتحكم
# =========================
st.sidebar.header("⚙️ Controls")
period_option = st.sidebar.selectbox("Select Analysis Frequency", ["Daily", "Weekly", "Monthly"])
chart_type = st.sidebar.radio("Chart Type", ["Line", "Bar"])

# Checkboxes لإظهار المؤشرات
show_SPY = st.sidebar.checkbox("SPY", value=True)
show_SP_Global = st.sidebar.checkbox("S&P Global", value=True)
show_MSCI = st.sidebar.checkbox("MSCI World", value=True)
show_VIX = st.sidebar.checkbox("VIX", value=True)
show_MOVE = st.sidebar.checkbox("MOVE Index", value=True)
show_GoldVol = st.sidebar.checkbox("Gold Volatility", value=True)

# =========================
# Load & Editable Stock Weights
# =========================
weights_file = "stocks_weights.csv"
weights_df = pd.read_csv(weights_file)
weights_df["weight"] = weights_df["weight"].astype(float)
weights_df["positive"] = weights_df["positive"].astype(int)

st.subheader("Adjust Weights & Sign")
weights_df = st.data_editor(weights_df, num_rows="dynamic", key="weights_editor")

# Restore default weights button
def restore_weights():
    df = pd.read_csv(weights_file)
    df["weight"] = df["weight"].astype(float)
    df["positive"] = df["positive"].astype(int)
    st.session_state["weights_editor"] = df
st.button("Restore Default Weights", on_click=restore_weights)

# =========================
# Date Inputs
# =========================
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())
st.button("Restore Default Dates", on_click=lambda: [st.session_state.update({"start_date": date.today() - pd.Timedelta(days=365), "end_date": date.today()})])

# =========================
# Fetch Market Data
# =========================
@st.cache_data(show_spinner=False)
def get_data(symbols, start, end):
    data = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    return data.dropna(how="all", axis=1)

symbols = weights_df["symbol"].tolist()
with st.spinner("Fetching market data…"):
    data = get_data(symbols, start_date, end_date)
if data.empty:
    st.error("No price data was returned for the selected period.")
    st.stop()

# =========================
# Compute Returns
# =========================
returns = data.pct_change().dropna(how="all")

# =========================
# Apply Weights, Sign, EWMA, Penalty Factor
# =========================
total_weight = weights_df["weight"].sum()
weighted = pd.DataFrame(index=returns.index)

for _, row in weights_df.iterrows():
    sign = 1 if row["positive"] == 1 else -1
    weighted[row["symbol"]] = returns[row["symbol"]] * (row["weight"] / total_weight) * sign

# EWMA smoothing
weighted_ewma = weighted.ewm(span=5, adjust=False).mean()

# Penalty factor: reduce index when high drawdown
drawdown = weighted_ewma.cumsum().apply(lambda x: x / x.cummax() - 1)
penalty = drawdown.clip(upper=0) * 0.5
weighted_adj = weighted_ewma + penalty

# =========================
# Build cumulative index & scale
# =========================
index_series = weighted_adj.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v) / (max_v - min_v) * 100 if max_v != min_v else pd.Series(50.0, index=index_series.index)

# =========================
# Compute performance metrics
# =========================
sharpe_like = weighted_adj.mean(axis=1).mean() / weighted_adj.mean(axis=1).std()
correlation_SPY = weighted_adj.mean(axis=1).corr(returns.get("^GSPC", pd.Series(dtype=float)))

# =========================
# Today's index
# =========================
today_pct = float(index_pct.iloc[-1])
color = "green" if today_pct >= 70 else "orange" if today_pct >= 40 else "red"
st.markdown(f"### Today's Index: **{today_pct:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# =========================
# Plot Chart
# =========================
plot_df = pd.DataFrame({"Index": index_pct})
if show_SPY and "^GSPC" in data.columns:
    plot_df["SPY"] = data["^GSPC"].pct_change().cumsum()
if show_VIX and "^VIX" in data.columns:
    plot_df["VIX"] = data["^VIX"].pct_change().cumsum()
# MOVE & GoldVol can be added if data available

if chart_type == "Line":
    fig = px.line(plot_df)
else:
    fig = px.bar(plot_df)

st.plotly_chart(fig, use_container_width=True)

# =========================
# Show table under chart
# =========================
st.subheader("Stock Weights Table")
st.dataframe(weights_df, use_container_width=True)

# =========================
# Save to GitHub if weights change
# =========================
def save_weights_to_github(df):
    token = os.environ.get("GITHUB_TOKEN")
    if token is None:
        st.warning("GitHub token not found. Skipping save.")
        return
    url = "https://api.github.com/repos/alparody/GeopoliticalTensionIndex/contents/stocks_weights.csv"
    csv_content = df.to_csv(index=False)
    import base64, json
    content_b64 = base64.b64encode(csv_content.encode()).decode()
    # Get SHA of current file
    r = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = r.json().get("sha", None)
    payload = {"message": "Update weights via app", "content": content_b64}
    if sha:
        payload["sha"] = sha
    r2 = requests.put(url, headers={"Authorization": f"token {token}"}, data=json.dumps(payload))
    if r2.status_code in [200,201]:
        st.success("Weights saved to GitHub!")
    else:
        st.error(f"Failed to save weights: {r2.text}")

if st.button("Save Weights to GitHub"):
    save_weights_to_github(weights_df)
