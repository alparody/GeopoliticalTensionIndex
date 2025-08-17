import pandas as pd

# نفترض إن البيانات موجودة في CSV
df = pd.read_csv("scenarios.csv")

# نحول العمود Date لتاريخ
df["Date"] = pd.to_datetime(df["Date"])

# نحسب العوائد اليومية لكل سيناريو
for col in ["S1 (متساوي)", "S2 (VIX أكبر)", "S3 (سلع أكبر)"]:
    df[f"{col}_Return"] = df[col].pct_change()

# نحسب العوائد التراكمية
for col in ["S1 (متساوي)", "S2 (VIX أكبر)", "S3 (سلع أكبر)"]:
    df[f"{col}_Cumulative"] = (1 + df[f"{col}_Return"]).cumprod()

# نحسب المقاييس
results = []
for col in ["S1 (متساوي)", "S2 (VIX أكبر)", "S3 (سلع أكبر)"]:
    returns = df[f"{col}_Return"].dropna()
    cumulative = df[f"{col}_Cumulative"].iloc[-1]
    volatility = returns.std()
    sharpe_like = returns.mean() / volatility if volatility > 0 else 0
    correlation = returns.corr(df["SPY"].pct_change())
    
    results.append({
        "Scenario": col,
        "Final Cumulative Return": cumulative,
        "Volatility": volatility,
        "Sharpe-like": sharpe_like,
        "Correlation with SPY": correlation
    })

results_df = pd.DataFrame(results)
print(results_df)
