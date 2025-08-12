import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, timedelta
import plotly.graph_objects as go

st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")
st.title("Geopolitical Tension Index (Colab Strategy)")

# -- قائمة الأسهم بعد تصحيح الرموز --
TICKERS = [
    'GC=F', 'CL=F',      # ذهب / نفط
    'LMT', 'NOC', 'RTX', # دفاع
    'XOM', 'CVX', 'BP',  # طاقة أمريكا
    'ZIM', 'AMKBY', 'CMRE',  # شحن عالمي
    '2222.SR', '2010.SR',    # أرامكو / سابك
    'QNBK.QA', 'QEWS.QA',    # قطر
    '7020.SR', 'DU.AE',      # الإمارات: اتصالات وسهم du
    'ORWE.CA', 'COMI.CA'     # مصر
]

# اختر الفترة
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("من:", date.today() - timedelta(days=365))
with col2:
    end_date = st.date_input("إلى:", date.today())

# أوزان الأسهم من الواجهة
st.sidebar.header("Weights (0–100%)")
weights = {t: st.sidebar.number_input(f"{t}", min_value=0.0, max_value=100.0, value=10.0, step=0.5) for t in TICKERS}

# تحميل البيانات
data = yf.download(TICKERS, start=start_date, end=end_date, interval="1d")['Close']
data = data.dropna(how='all', axis=1)  # إزالة أعمدة غير متوفرة

# حساب المؤشر Colab style
returns = data.pct_change().dropna()
weighted = pd.DataFrame({t: returns[t] * (weights.get(t,0)/100) for t in returns.columns})
index_series = weighted.sum(axis=1).cumsum()

# جدول و رسم
st.subheader("Latest Tension Index values")
st.line_chart(index_series.rename("Tension Index"))

df_latest = pd.DataFrame({
    "Date": index_series.index,
    "Tension Index": index_series.values
}).tail(10).set_index("Date")
st.write(df_latest.style.format("{:.3f}"))

st.caption("Powered by real returns × weights, cumulative sum (exact Colab logic).")
