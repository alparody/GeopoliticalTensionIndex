import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# ------------------------
# إعدادات الصفحة
# ------------------------
st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")

st.title("📈 Geopolitical Tension Index")

# ------------------------
# تعريف الأسهم + أوزانها
# ------------------------
tickers = {
    'GC=F': 'Gold Futures',
    'CL=F': 'Crude Oil Futures',
    'LMT': 'Lockheed Martin',
    'NOC': 'Northrop Grumman',
    'RTX': 'RTX Corp',
    'XOM': 'Exxon Mobil',
    'CVX': 'Chevron',
    'BP': 'BP PLC',
    'ZIM': 'ZIM Integrated Shipping',
    'AMKBY': 'A.P. Moller Maersk',
    'CMRE': 'Costamare Inc',
    # أمثلة لأسهم شرق أوسطية موجودة فعلاً على Yahoo Finance:
    'ADNOC Distribution.AE': 'ADNOC Distribution',
    'QNBK.QA': 'Qatar National Bank'
}

# ------------------------
# اختيار التواريخ
# ------------------------
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("من تاريخ", datetime.date(2022, 1, 1))
with col2:
    end_date = st.date_input("إلى تاريخ", datetime.date.today())

# ------------------------
# إدخال الأوزان
# ------------------------
weights = {}
st.sidebar.subheader("أوزان الأسهم (%)")
for ticker, name in tickers.items():
    weights[ticker] = st.sidebar.slider(f"{name} ({ticker})", 0, 100, 10)

# ------------------------
# تحميل البيانات
# ------------------------
try:
    data_all = yf.download(list(tickers.keys()), start=start_date, end=end_date, interval="1d")['Close']
except Exception as e:
    st.error(f"خطأ في تحميل البيانات: {e}")
    st.stop()

# ------------------------
# حساب العائدات والمؤشر
# ------------------------
returns = data_all.pct_change(fill_method=None)
weighted_returns = pd.DataFrame()

for ticker in tickers.keys():
    if ticker in returns.columns:
        weighted_returns[ticker] = returns[ticker] * (weights[ticker] / 100)

index_series = weighted_returns.sum(axis=1).cumsum()

# ------------------------
# عرض البيانات والرسوم
# ------------------------
st.subheader("المؤشر العام")
st.line_chart(index_series)

st.subheader("البيانات الخام")
st.dataframe(data_all)

st.subheader("العائدات اليومية")
st.dataframe(returns)
