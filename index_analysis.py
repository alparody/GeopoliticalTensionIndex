import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta

def load_indices(file_path="indices.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_index_performance(ticker):
    today = datetime.today()
    periods = {
        "daily": today - timedelta(days=1),
        "weekly": today - timedelta(days=7),
        "monthly": today - timedelta(days=30),
        "yearly": today - timedelta(days=365),
    }
    
    data = yf.download(ticker, start=periods["yearly"], end=today+timedelta(days=1), progress=False)
    if data.empty:
        return {p: None for p in periods}
    
    latest = data["Close"].iloc[-1]
    results = {}
    
    for period, start_date in periods.items():
        subset = data[data.index >= start_date]
        if subset.empty:
            results[period] = None
        else:
            first_val = subset["Close"].iloc[0]
            results[period] = round(((latest - first_val) / first_val) * 100, 2)
    
    return results

def build_results():
    indices = load_indices()
    all_results = []
    
    for idx in indices:
        perf = get_index_performance(idx["YahooTicker"])
        all_results.append({
            "Country": idx["Country"],
            "Index": idx["MainIndexName"],
            "Ticker": idx["YahooTicker"],
            **perf
        })
    return pd.DataFrame(all_results)

if __name__ == "__main__":
    df = build_results()
    print(df)
    df.to_csv("index_performance.csv", index=False)
