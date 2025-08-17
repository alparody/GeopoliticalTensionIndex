import pandas as pd
import matplotlib.pyplot as plt

# مثال: افترض إن عندك DataFrame اسمه df فيه عمود التاريخ causality_index
# df = pd.read_csv("causality_results.csv", parse_dates=["date"])

# ✅ قائمة فترات الأزمات
periods = [
    {"name": "Russia-Ukraine invasion (early)", "start": "2022-02-24", "end": "2022-05-31"},
    {"name": "Israel-Hamas (Oct 2023)", "start": "2023-10-07", "end": "2023-12-15"},
    {"name": "Global market shock (Mar 2020)", "start": "2020-02-15", "end": "2020-05-31"},
    {"name": "Global Financial Crisis (2008)", "start": "2008-09-01", "end": "2009-03-31"},
    {"name": "Eurozone Debt Crisis (2011)", "start": "2011-06-01", "end": "2012-01-31"},
    {"name": "Brexit shock (2016)", "start": "2016-06-01", "end": "2016-09-30"},
    {"name": "US Elections (2020)", "start": "2020-10-01", "end": "2020-12-31"},
    {"name": "Inflation & Fed Rate Hikes (2022)", "start": "2022-06-01", "end": "2022-12-31"},
    {"name": "SVB Banking Crisis (2023)", "start": "2023-03-01", "end": "2023-05-31"},
]

# ✅ دالة للتحليل داخل الفترات
results = []
for p in periods:
    mask = (df["date"] >= p["start"]) & (df["date"] <= p["end"])
    sub = df.loc[mask]

    if not sub.empty:
        avg_val = sub["causality_index"].mean()
        std_val = sub["causality_index"].std()
        results.append({
            "Period": p["name"],
            "Start": p["start"],
            "End": p["end"],
            "Mean Causality": round(avg_val, 4),
            "Std Dev": round(std_val, 4),
            "Data Points": len(sub)
        })

# ✅ نحول النتائج لجدول DataFrame
results_df = pd.DataFrame(results)

# نعرض النتائج
print("\n=== Causality Backtest Results ===\n")
print(results_df.to_string(index=False))

# ✅ رسم بياني يوضح المؤشر مع الفترات
plt.figure(figsize=(14,6))
plt.plot(df["date"], df["causality_index"], label="Causality Index", color="blue")

# تظليل الفترات
for p in periods:
    plt.axvspan(pd.to_datetime(p["start"]), pd.to_datetime(p["end"]),
                color="red", alpha=0.2, label=p["name"])

plt.title("Causality Index with Crisis Periods")
plt.xlabel("Date")
plt.ylabel("Causality Index")
plt.legend(loc="upper right", fontsize=8)
plt.show()
