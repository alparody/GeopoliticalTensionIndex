import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import streamlit as st

# دالة لحساب ورسم مؤشر GTI
def run_gti_test():
    try:
        # تحميل ملف الأوزان
        weights_df = pd.read_csv("weights.csv")

        # استخراج الرموز والأوزان
        symbols = weights_df["Symbol"].tolist()
        weights = weights_df["Weight"].tolist()

        st.write("### 📊 GTI Test Run")
        st.write("Using weights file with symbols:", symbols)

        # تحميل البيانات من Yahoo Finance
        data = yf.download(symbols, period="1mo")["Adj Close"]

        # لو عمود واحد بيجي كـ Series، نخليه DataFrame
        if isinstance(data, pd.Series):
            data = data.to_frame()

        # حساب normalized returns
        norm_data = data / data.iloc[0]

        # ضرب في الأوزان
        weighted = norm_data.mul(weights, axis=1)

        # حساب المؤشر النهائي
        gti = weighted.sum(axis=1)

        # رسم
        fig, ax = plt.subplots(figsize=(10, 4))
        gti.plot(ax=ax, label="GTI", color="blue")
        ax.set_title("Geopolitical Tension Index (Test)")
        ax.legend()

        st.pyplot(fig)

    except Exception as e:
        st.error(f"⚠️ Error running GTI test: {e}")
