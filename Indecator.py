import streamlit as st
import pandas as pd
import numpy as np
from gti_test import run_gti_test

def max_drawdown(returns):
    cumulative = (1 + returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    return drawdown.min()

def run_gti_with_optimization():
    df, results_df = run_gti_test(return_full=True)  # عدلنا gti_test يرجع البيانات كاملة
    
    scenarios = []
    rebalance_period = 63  # تقريبًا ربع سنة (63 يوم تداول)
    
    for scenario in results_df["Scenario"].unique():
        returns = df[f"{scenario}_Return"].dropna()
        
        # تقسيم الفترات (Quarterly Rebalancing)
        weighted_returns = []
        for i in range(0, len(returns), rebalance_period):
            window = returns.iloc[i:i+rebalance_period]
            vol = window.std()
            
            # استراتيجية بسيطة: وزن أقل مع تقلب أعلى
            weight = 1 / (1 + vol*100)
            weighted_window = window * weight
            weighted_returns.append(weighted_window)
        
        weighted_returns = pd.concat(weighted_returns)
        
        # حساب المقاييس
        final_cumulative = (1 + weighted_returns).prod() - 1
        volatility = weighted_returns.std()
        sharpe_like = weighted_returns.mean() / volatility if volatility > 0 else 0
        mdd = max_drawdown(weighted_returns)
        
        scenarios.append({
            "Scenario": scenario,
            "Final Cumulative Return": final_cumulative,
            "Volatility": volatility,
            "Sharpe-like": sharpe_like,
            "Max Drawdown": mdd
        })
    
    optimized_df = pd.DataFrame(scenarios)
    return optimized_df

# واجهة Streamlit
st.title("📊 Geopolitical Tension Index (GTI) - Enhanced")

if st.sidebar.button("Run GTI Test (Optimized)"):
    optimized_results = run_gti_with_optimization()
    st.write("### Optimized Results")
    st.dataframe(optimized_results)
