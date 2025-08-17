import streamlit as st
import pandas as pd

def run_gti_test():
    # --------- بيانات تجريبية Placeholder ---------
    data = {
        "Date": pd.date_range("2024-01-01", periods=10, freq="D"),
        "SPY": [470, 472, 468, 465, 469, 471, 473, 474, 470, 469],
        "GLD": [185, 186, 184, 183, 185, 186, 187, 188, 186, 185],
        "WTI": [72, 73, 71, 70, 72, 74, 73, 75, 72, 71],
        "VIX": [13, 14, 15, 16, 14, 13, 12, 13, 14, 15]
    }
    df = pd.DataFrame(data)

    # --------- السيناريوهات ---------
    scenarios = {
        "S1 (متساوي)": {"SPY": 0.25, "GLD": 0.25, "WTI": 0.25, "VIX": 0.25},
        "S2 (VIX أكبر)": {"SPY": 0.2, "GLD": 0.2, "WTI": 0.2, "VIX": 0.4},
        "S3 (سلع أكبر)": {"SPY": 0.2, "GLD": 0.4, "WTI": 0.3, "VIX": 0.1},
    }

    # --------- حساب المؤشر ---------
    for s_name, weights in scenarios.items():
        df[s_name] = (
            df["SPY"] * weights["SPY"]
            + df["GLD"] * weights["GLD"]
            + df["WTI"] * weights["WTI"]
            + df["VIX"] * weights["VIX"]
        )

    # --------- عرض النتايج ---------
    st.write("📊 نتائج اختبار السيناريوهات المختلفة للأوزان:")
    st.dataframe(df)
