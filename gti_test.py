import pandas as pd
from data_loader import load_stock_data

def run_gti_test():
    tickers = ["SPY", "GLD", "VIX"]  # مثال للتجربة
    data = load_stock_data(tickers)

    # تجهيز مقترحات مختلفة للأوزان
    weight_sets = [
        {"SPY": 0.5, "GLD": 0.3, "VIX": 0.2},
        {"SPY": 0.4, "GLD": 0.4, "VIX": 0.2},
        {"SPY": 0.3, "GLD": 0.3, "VIX": 0.4},
    ]

    results = []

    for weights in weight_sets:
        df = data.pivot(index="Date", columns="Ticker", values="Close").dropna()
        
        # حساب المؤشر كمزيج مرجح
        df["GTI"] = sum(df[ticker] * weight for ticker, weight in weights.items())
        
        final_value = df["GTI"].iloc[-1]
        results.append({
            "Weights": weights,
            "Final GTI": round(final_value, 2)
        })

    return pd.DataFrame(results)
