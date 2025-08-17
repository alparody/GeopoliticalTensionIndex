def run_gti_test():
    import yfinance as yf
    import pandas as pd

    tickers = ["SPY", "GLD", "VIXY"]  # أي أسهم/مؤشرات انت عايز تجرب بيها
    raw_data = yf.download(tickers, start="2020-01-01", end="2024-01-01")

    # نجيب بس Adj Close
    data = raw_data.xs("Adj Close", axis=1, level=1)

    # نجرب أوزان مختلفة
    weights_list = [
        {"SPY": 0.5, "GLD": 0.3, "VIXY": 0.2},
        {"SPY": 0.4, "GLD": 0.4, "VIXY": 0.2},
        {"SPY": 0.6, "GLD": 0.2, "VIXY": 0.2},
    ]

    results = []
    for weights in weights_list:
        weighted_sum = sum(data[ticker].pct_change().fillna(0) * w for ticker, w in weights.items())
        score = weighted_sum.cumsum().iloc[-1]  # آخر قيمة كمثال للنتيجة
        results.append({"weights": weights, "final_score": score})

    results_df = pd.DataFrame(results)
    print(results_df)
    return results_df
