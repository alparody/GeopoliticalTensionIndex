import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime

# تحميل بيانات الأسعار
@st.cache_data
def load_data(tickers, start="2000-01-01", end=datetime.today().strftime("%Y-%m-%d")):
    data = yf.download(tickers, start=start, end=end)["Adj Close"]
    return data

# حساب العائدات النسبية
def calculate_returns(prices):
    return prices.pct_change().dropna()

# إعادة موازنة المحفظة
def rebalance_portfolio(returns, weights, freq="Q"):
    weights = weights / weights.sum()  # normalize
    portfolio_returns = pd.Series(dtype=float)

    # نعيد الوزن كل فترة (ربع سنوي مثلاً)
    for start_date, period_data in returns.resample(freq):
        for ticker in weights.index:
            if ticker not in period_data.columns:
                period_data[ticker] = 0
        period_data = period_data.fillna(0)
        period_returns = (period_data * weights).sum(axis=1)
        portfolio_returns = pd.concat([portfolio_returns, period_returns])

    return portfolio_returns

# حساب Max Drawdown
def max_drawdown(cumulative):
    roll_max = cumulative.cummax()
    drawdown = (cumulative - roll_max) / roll_max
    return drawdown.min()

# حساب Rolling Sharpe Ratio
def rolling_sharpe(returns, window=252):
    mean = returns.rolling(window).mean()
    std = returns.rolling(window).std()
    sharpe = (mean / std) * np.sqrt(252)
    return sharpe

def run_gti_test():
    st.title("Geopolitical Tension Index - Scenarios Test")

    # تحميل السيناريوهات
    weights_df = pd.read_csv("stocks_weights.csv", index_col=0)

    # تحميل البيانات
    tickers = weights_df.columns.tolist()
    prices = load_data(tickers)
    returns = calculate_returns(prices)

    results = []

    for scenario in weights_df.index:
        weights = weights_df.loc[scenario]
        port_returns = rebalance_portfolio(returns, weights, freq="Q")
        cumulative = (1 + port_returns).cumprod()
        sharpe = port_returns.mean() / port_returns.std() * np.sqrt(252)
        mdd = max_drawdown(cumulative)
        rolling_sharpe_ratio = rolling_sharpe(port_returns)

        results.append({
            "Scenario": scenario,
            "CAGR": (cumulative.iloc[-1] ** (252/len(port_returns))) - 1,
            "Sharpe": sharpe,
            "Max Drawdown": mdd
        })

        st.line_chart(cumulative, height=300)

    results_df = pd.DataFrame(results)
    st.dataframe(results_df.set_index("Scenario"))
    st.line_chart(rolling_sharpe_ratio, height=200)
