# streamlit_app.py
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import date, timedelta

# ===== إعدادات واجهة المستخدم =====
st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")

st.title("🌍 Geopolitical Tension Index")
st.markdown("This dashboard shows the geopolitical tension index using Colab strategy.")

# ===== اختيار التاريخ من الواجهة =====
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From:", date.today() - timedelta(days=365))
with col2:
    end_date = st.date_input("To:", date.today())

# ===== تعريف الأسهم والأوزان =====
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


# ===== جلب البيانات =====
st.write("Fetching market data...")
data_all = yf.download(list(tickers.keys()), start=start_date, end=end_date, interval="1d")['Close']

# ===== معالجة في حالة وجود MultiIndex أو لا =====
if isinstance(data_all, pd.Series):
    close_df = data_all.to_frame()
elif isinstance(data_all.columns, pd.MultiIndex):
    close_df = data_all.copy()
else:
    close_df = data_all.copy()

# ===== حساب المؤشر بنفس طريقة Colab =====
window_days = 3  # نفس نافذة Colab
pct_change = close_df.pct_change(periods=window_days) * 100
weighted_scores = pd.DataFrame()

for t, w in tickers.items():
    if t in pct_change.columns:
        weighted_scores[t] = pct_change[t] * w

# المؤشر الإجمالي
weighted_scores["TotalIndex"] = weighted_scores.sum(axis=1)

# ===== التطبيع بين 0 و 100 =====
min_val = weighted_scores["TotalIndex"].min()
max_val = weighted_scores["TotalIndex"].max()
weighted_scores["NormalizedIndex"] = 100 * (weighted_scores["TotalIndex"] - min_val) / (max_val - min_val)

# ===== عرض الجدول =====
st.subheader("📊 Tension Index Table")
st.dataframe(weighted_scores[["TotalIndex", "NormalizedIndex"]].round(3))

# ===== رسم بياني تفاعلي =====
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=weighted_scores.index,
    y=weighted_scores["NormalizedIndex"],
    mode='lines+markers',
    name='Tension Index',
    line=dict(color='red')
))

fig.update_layout(
    title="Geopolitical Tension Index Over Time",
    xaxis_title="Date",
    yaxis_title="Index (0-100)",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)
