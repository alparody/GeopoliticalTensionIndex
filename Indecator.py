import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import os

# ---------------------- إعداد الصفحة ----------------------
st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")
st.title("Political Tension Index (0–100 Scale)")

# ---------------------- تحميل بيانات الأسهم والمؤشرات ----------------------
# CSV الأصلي للـ weights مع الأعمدة: symbol, weight, positive, description
weights_file = "stocks_weights.csv"
default_weights = pd.read_csv(weights_file)
weights_df = default_weights.copy()

# ---------------------- Sidebar التواريخ ----------------------
st.sidebar.header("📅 Select Date Range")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("From", date.today() - timedelta(days=365))
with col2:
    end_date = st.date_input("To", date.today())
if st.sidebar.button("Restore Today"):
    start_date = date.today() - timedelta(days=365)
    end_date = date.today()

# ---------------------- Sidebar المؤشرات ----------------------
st.sidebar.header("📈 Show Additional Indicators")
show_SPY = st.sidebar.checkbox("SPY", True)
show_SP_Global = st.sidebar.checkbox("S&P Global", True)
show_MSCI = st.sidebar.checkbox("MSCI World", True)
show_VIX = st.sidebar.checkbox("VIX", True)
show_MOVE = st.sidebar.checkbox("MOVE Index", True)
show_GoldVol = st.sidebar.checkbox("Gold Volatility", True)

# ---------------------- Sidebar الرسم ----------------------
st.sidebar.header("📊 Chart Type")
chart_type = st.sidebar.radio("Choose Chart Type", ["Line", "Bar"])

# ---------------------- Sidebar تعديل الأوزان ----------------------
st.sidebar.header("⚖️ Edit Weights")
st.sidebar.markdown("Edit the weight and sign (positive=1 / negative=0) and click Save.")
edited_weights = st.sidebar.experimental_data_editor(weights_df, num_rows="dynamic")

# Restore Default
if st.sidebar.button("Restore Default Weights"):
    edited_weights = default_weights.copy()

# ---------------------- حفظ التعديلات على GitHub ----------------------
if st.sidebar.button("Save Weights to GitHub"):
    token = st.secrets["GITHUB_TOKEN"]
    import requests, base64, json
    url = "https://api.github.com/repos/<username>/<repo>/contents/stocks_weights.csv"  # ضع بياناتك
    csv_content = edited_weights.to_csv(index=False)
    message = "Update weights via Streamlit"
    content_bytes = base64.b64encode(csv_content.encode()).decode()
    headers = {"Authorization": f"token {token}"}
    r = requests.get(url, headers=headers)
    sha = r.json()["sha"]
    data = {"message": message, "content": content_bytes, "sha": sha}
    resp = requests.put(url, headers=headers, data=json.dumps(data))
    if resp.status_code == 200:
        st.success("Weights saved to GitHub successfully!")
    else:
        st.error("Failed to save to GitHub.")

# ---------------------- جلب بيانات السوق ----------------------
symbols = edited_weights["symbol"].tolist()
data = yf.download(symbols, start=start_date, end=end_date, auto_adjust=True, progress=False)["Close"].dropna(how="all")

if data.empty:
    st.error("No data returned for selected symbols.")
    st.stop()

# ---------------------- حساب المؤشر ----------------------
weighted_returns = pd.DataFrame(index=data.index)

# Normalize each asset (z-score)
z_data = (data - data.mean()) / data.std()

# EWMA returns
returns = z_data.pct_change().ewm(span=10, adjust=False).mean()

total_weight = edited_weights["weight"].sum()
for _, row in edited_weights.iterrows():
    sign = 1 if int(row["positive"]) == 1 else -1
    symbol = row["symbol"]
    if symbol in returns.columns:
        weighted_returns[symbol] = returns[symbol] * (row["weight"] / total_weight) * sign

# Cumulative sum
index_series = weighted_returns.sum(axis=1).cumsum()

# Scale 0-100
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v) / (max_v - min_v) * 100

# ---------------------- مؤشرات الأداء ----------------------
daily_returns = index_pct.pct_change().dropna()
volatility = daily_returns.std()
sharpe_like = daily_returns.mean() / volatility if volatility > 0 else 0
corr_SPY = daily_returns.corr(data["SPY"].pct_change()) if "SPY" in data.columns else np.nan
corr_VIX = daily_returns.corr(data["^VIX"].pct_change()) if "^VIX" in data.columns else np.nan

# ---------------------- الرسم ----------------------
fig = go.Figure()
fig.add_trace(go.Scatter(x=index_pct.index, y=index_pct, name="GTI", mode="lines"))

# إضافات المؤشرات
if show_SPY and "SPY" in data.columns:
    fig.add_trace(go.Scatter(x=data.index, y=data["SPY"], name="SPY", mode="lines"))
if show_SP_Global and "SPGLOBE" in data.columns:
    fig.add_trace(go.Scatter(x=data.index, y=data["SPGLOBE"], name="S&P Global", mode="lines"))
if show_MSCI and "MSCI" in data.columns:
    fig.add_trace(go.Scatter(x=data.index, y=data["MSCI"], name="MSCI World", mode="lines"))
if show_VIX and "^VIX" in data.columns:
    fig.add_trace(go.Scatter(x=data.index, y=data["^VIX"], name="VIX", mode="lines"))
if show_MOVE and "MOVE" in data.columns:
    fig.add_trace(go.Scatter(x=data.index, y=data["MOVE"], name="MOVE Index", mode="lines"))
if show_GoldVol and "GOLDVOL" in data.columns:
    fig.add_trace(go.Scatter(x=data.index, y=data["GOLDVOL"], name="Gold Volatility", mode="lines"))

fig.update_layout(title="Geopolitical Tension Index", xaxis_title="Date", yaxis_title="Value (%)")
st.plotly_chart(fig, use_container_width=True)

# ---------------------- الجدول تحت الرسم ----------------------
st.subheader("📊 Adjusted Weights & Sign Table")
st.dataframe(edited_weights)

# ---------------------- ملخص الأداء ----------------------
st.subheader("📌 Performance Metrics")
st.write(f"Volatility: {volatility:.4f}")
st.write(f"Sharpe-like ratio: {sharpe_like:.4f}")
st.write(f"Correlation with SPY: {corr_SPY:.4f}")
st.write(f"Correlation with VIX: {corr_VIX:.4f}")
