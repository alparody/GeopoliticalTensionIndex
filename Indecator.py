# مؤشر Geopolitical Tension Index متطور - Streamlit
# مكتبات مطلوبة:
# pip install streamlit pandas yfinance plotly numpy scipy

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from datetime import date

# -------------------------------
# إعداد الصفحة والـ sidebar
# -------------------------------
st.set_page_config(page_title="Advanced Political Tension Index", layout="wide")
st.title("Advanced Political Tension Index (0–100 Scale)")

# Sidebar لإعدادات التواريخ
st.sidebar.header("Date Range")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("From Date", date.today() - pd.Timedelta(days=365))
with col2:
    end_date = st.date_input("To Date", date.today())

if st.sidebar.button("Restore Default Dates"):
    start_date = date.today() - pd.Timedelta(days=365)
    end_date = date.today()

# Sidebar لاختيار نوع الرسم
chart_type = st.sidebar.selectbox("Chart Type", ["Line", "Bar"])

# -------------------------------
# تحميل ملف الأسهم والأوزان
# -------------------------------
@st.cache_data
def load_weights():
    df = pd.read_csv("stocks_weights.csv")  # لازم يكون موجود بنفس المجلد
    df["weight"] = df["weight"].astype(float)
    df["positive"] = df["positive"].astype(int)
    return df

weights_df = load_weights()

# عرض جدول لتعديل الأوزان مباشرة
st.subheader("Adjust Weights / Positive Sign")
weights_df = st.experimental_data_editor(weights_df, num_rows="dynamic")

# -------------------------------
# تحميل بيانات السوق باستخدام yfinance
# -------------------------------
@st.cache_data(show_spinner=False)
def get_market_data(symbols, start, end):
    data = yf.download(symbols, start=start, end=end, auto_adjust=True)["Close"]
    return data.dropna(how="all", axis=1)

symbols = weights_df["symbol"].tolist()
with st.spinner("Fetching market data…"):
    data = get_market_data(symbols, start_date, end_date)

if data.empty:
    st.error("No data returned for selected symbols.")
    st.stop()

# -------------------------------
# حساب المؤشر
# -------------------------------
# 1. حساب العوائد اليومية
returns = data.pct_change().dropna(how="all")

# 2. حساب z-score لكل أصل لتقليل تأثير القيم الكبيرة
zscore_returns = (returns - returns.mean()) / returns.std()

# 3. تعديل الوزن حسب sign
total_weight = weights_df["weight"].sum()
weighted_returns = pd.DataFrame(index=zscore_returns.index)
for _, row in weights_df.iterrows():
    sign = 1 if row["positive"] == 1 else -1
    if row["symbol"] in zscore_returns.columns:
        weighted_returns[row["symbol"]] = zscore_returns[row["symbol"]] * (row["weight"]/total_weight) * sign

# 4. استخدام EWMA لتقليل الضوضاء
ewma_span = 10  # يمكن تعديله
index_series = weighted_returns.sum(axis=1).ewm(span=ewma_span).mean()

# 5. تحويل المؤشر 0–100
min_v, max_v = index_series.min(), index_series.max()
index_scaled = (index_series - min_v) / (max_v - min_v) * 100

# -------------------------------
# عرض القيمة الحالية
# -------------------------------
today_index = float(index_scaled.iloc[-1])
color = "green" if today_index >= 70 else "orange" if today_index >= 40 else "red"
st.markdown(f"### Today's Index: **{today_index:.2f}%**")
st.markdown(f"<h2 style='color:{color};'>■</h2>", unsafe_allow_html=True)

# -------------------------------
# اختيار نوع الرسم وعرضه
# -------------------------------
st.subheader("Index Chart")
if chart_type == "Line":
    st.line_chart(index_scaled, height=300)
else:
    st.bar_chart(index_scaled, height=300)

# -------------------------------
# مؤشرات الأداء لكل أصل
# -------------------------------
st.subheader("Performance Metrics per Symbol")
metrics = []
for col in weighted_returns.columns:
    r = weighted_returns[col].dropna()
    if len(r) == 0:
        continue
    metrics.append({
        "Symbol": col,
        "Volatility": r.std(),
        "Sharpe-like": r.mean() / r.std() if r.std() > 0 else 0,
        "Correlation with Index": r.corr(index_scaled)
    })
metrics_df = pd.DataFrame(metrics)
st.dataframe(metrics_df)

# -------------------------------
# زر تحميل بيانات المؤشر
# -------------------------------
st.download_button(
    label="Download Index Data (0–100)",
    data=index_scaled.to_csv().encode("utf-8"),
    file_name="advanced_geopolitical_index.csv",
    mime="text/csv"
)
