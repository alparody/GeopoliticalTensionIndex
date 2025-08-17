import yfinance as yf
import pandas as pd

def run_gti_test():
    tickers = ["^VIX", "^GSPC", "CL=F", "GC=F"]  # VIX, S&P500, Oil, Gold
    
    raw_data = yf.download(tickers, start="2020-01-01", end="2024-12-31")
    
    # التعامل مع MultiIndex
    if isinstance(raw_data.columns, pd.MultiIndex):
        data = raw_data["Adj Close"]
    else:
        data = raw_data[["Adj Close"]]
    
    # حساب العوائد اليومية
    returns = data.pct_change().dropna()

    # مقترحات للأوزان
    weight_sets = {
        "Scenario 1 (Balanced)": {"^VIX": 0.25, "^GSPC": 0.25, "CL=F": 0.25, "GC=F": 0.25},
        "Scenario 2 (VIX Heavy)": {"^VIX": 0.4, "^GSPC": 0.2, "CL=F": 0.2, "GC=F": 0.2},
        "Scenario 3 (Commodities Heavy)": {"^VIX": 0.2, "^GSPC": 0.2, "CL=F": 0.3, "GC=F": 0.3},
        "Scenario 4 (Equity Light)": {"^VIX": 0.3, "^GSPC": 0.1, "CL=F": 0.3, "GC=F": 0.3},
    }

    results = []

    for scenario, weights in weight_sets.items():
        gti = (
            returns["^VIX"] * weights["^VIX"]
            - returns["^GSPC"] * weights["^GSPC"]
            + returns["CL=F"] * weights["CL=F"]
            + returns["GC=F"] * weights["GC=F"]
        )
        avg = gti.mean()
        vol = gti.std()
        score = avg / vol if vol != 0 else 0
        
        results.append([scenario, avg, vol, score])

    df_results = pd.DataFrame(results, columns=["Scenario", "Average Return", "Volatility", "Sharpe-like Score"])
    return df_results
