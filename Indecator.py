import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import date

# =======================
# Settings
# =======================
TICKERS = [
    # Commodities
    'GC=F',  # Gold
    'CL=F',  # Crude Oil

    # US Defense
    'LMT', 'NOC', 'RTX',

    # US Energy
    'XOM', 'CVX', 'BP',

    # Shipping
    'ZIM', 'AMKBY', 'CMRE',

    # Middle East - Saudi Arabia
    '2222.SR',  # Saudi Aramco
    '2010.SR',  # SABIC

    # Middle East - Qatar
    'QNBK.QA',  # Qatar National Bank
    'QEWS.QA',  # Qatar Electricity & Water

    # Middle East - UAE
    'EMAAR.DU',     # Emaar Properties
    'ETISALAT.AD',  # Etisalat UAE

    # Middle East - Egypt
    'ORWE.CA',  # Orascom Development
    'COMI.CA'   # Commercial International Bank
]

# Editable weights
WEIGHTS = {
    'GC=F': 0.1, 'CL=F': 0.1,
    'LMT': 0.05, 'NOC': 0.05, 'RTX': 0.05,
    'XOM': 0.05, 'CVX': 0.05, 'BP': 0.05,
    'ZIM': 0.05, 'AMKBY': 0.05, 'CMRE': 0.05,
    '2222.SR': 0.08, '2010.SR': 0.05,
    'QNBK.QA': 0.05, 'QEWS.QA': 0.03,
    'EMAAR.DU': 0.03, 'ETISALAT.AD': 0.03,
    'ORWE.CA': 0.02, 'COMI.CA': 0.02
}

# =======================
# Streamlit UI
# =======================
st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")

st.title("🌍 Geopolitical Tension Index")
st.markdown("مؤشر يرصد التوترات الجيوسياسية بناءً على أداء قطاعات وشركات مختارة عالميًا وإقليميًا.")

# Date picker
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("من:", date(2022, 1, 1))
with col2:
    end_date = st.date_input("إلى:", date.today())

# =======================
# Data Download
# =======================
data_all = yf.download(TICKERS, start=start_date, end=end_date, interval="1d")['Close']

# =======================
# Index Calculation
# =======================
returns = data_all.pct_change().dropna()
weighted_returns = returns.copy()

for ticker in WEIGHTS:
    if ticker in weighted_returns.columns:
        weighted_returns[ticker] = weighted_returns[ticker] * WEIGHTS[ticker]

# المؤشر الإجمالي
index_series = weighted_returns.sum(axis=1) * 100  # كنسبة مئوية
index_series = (index_series - index_series.min()) / (index_series.max() - index_series.min()) * 100  # Normalize 0-100

# =======================
# Display Table
# =======================
st.subheader("📊 آخر بيانات المؤشر")
latest_df = pd.DataFrame({
    "Date": index_series.index,
    "Tension Index": index_series.values
}).set_index("Date").tail(10)

st.dataframe(latest_df.style.format({"Tension Index": "{:.2f}"}))

# =======================
# Chart
# =======================
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=index_series.index, 
    y=index_series.values,
    mode='lines',
    name='Tension Index',
    line=dict(color='red', width=2)
))

fig.update_layout(
    title="📈 Geopolitical Tension Index (0-100)",
    xaxis_title="Date",
    yaxis_title="Index",
    hovermode="x unified",
    height=500
)

st.plotly_chart(fig, use_container_width=True)
