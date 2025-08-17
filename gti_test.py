import pandas as pd
import yfinance as yf
import numpy as np

# =========================
# 1. تحميل البيانات
# =========================
tickers = ["SPY", "GLD", "^VIX"]
data = yf.download(tickers, start="2020-01-01", end="2024-12-31")["Adj Close"]
data = data.dropna()

# حساب العائد اليومي
returns = data.pct_change().dropna()

# =========================
# 2. تعريف فترات الأزمات
# =========================
crisis_periods = [
    {"name": "Russia-Ukraine invasion (early)", "start": "2022-02-24", "end": "2022-05-31"},
    {"name": "Israel-Hamas (Oct 2023)", "start": "2023-10-07", "end": "2023-12-15"},
    {"name": "Global market shock (Mar 2020)", "start": "2020-02-15", "end": "2020-05-31"},
    {"name": "COVID second wave", "start": "2020-09-01", "end": "2020-12-31"},
    {"name": "US Inflation Shock", "start": "2022-06-01", "end": "2022-09-30"},
]

# =========================
# 3. سيناريوهات الأوزان
# =========================
weight_sets = {
    "Set1 (Base)": {"SPY": 0.6, "GLD": 0.3, "^VIX": 0.1},
    "Set2 (More Gold)": {"SPY": 0.5, "GLD": 0.4, "^VIX": 0.1},
    "Set3 (More VIX)": {"SPY": 0.5, "GLD": 0.2, "^VIX": 0.3},
    "Set4 (Balanced)": {"SPY": 0.4, "GLD": 0.3, "^VIX": 0.3},
}

# =========================
# 4. حساب المؤشر والنتائج
# =========================
all_results = []

for set_name, weights in weight_sets.items():
    # حساب المؤشر
    portfolio_returns = (
        returns["SPY"] * weights["SPY"]
        + returns["GLD"] * weights["GLD"]
        - returns["^VIX"] * weights["^VIX"]  # عكس VIX
    )
    index = (1 + portfolio_returns).cumprod() * 100
    
    for p in crisis_periods:
        mask = (returns.index >= p["start"]) & (returns.index <= p["end"])
        sub_ret = portfolio_returns.loc[mask]
        sub_index = index.loc[mask]

        result = {
            "Weight_Set": set_name,
            "Period": p["name"],
            "Start": p["start"],
            "End": p["end"],
            "Mean_Daily_Return": sub_ret.mean(),
            "Volatility_Daily": sub_ret.std(),
            "Start_Value": sub_index.iloc[0],
            "End_Value": sub_index.iloc[-1],
            "Max_Value": sub_index.max(),
            "Min_Value": sub_index.min(),
            "Max_Drawdown": (sub_index.min() - sub_index.max()) / sub_index.max(),
            "Corr_with_VIX": sub_ret.corr(returns["^VIX"].loc[mask]),
            "Corr_with_Gold": sub_ret.corr(returns["GLD"].loc[mask]),
        }
        all_results.append(result)

# =========================
# 5. إخراج الجدول النهائي
# =========================
df_results = pd.DataFrame(all_results)
pd.set_option("display.float_format", "{:.6f}".format)

print(df_results)
