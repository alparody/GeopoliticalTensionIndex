import pandas as pd
import matplotlib.pyplot as plt

# مثال: افترض إن عندك DataFrame اسمه df فيه عمود التاريخ causality_index
# df = pd.read_csv("causality_results.csv", parse_dates=["date"])

# تعريف فترات الأزمات
periods = [
    {"name": "2008 Financial Crisis", "start": "2008-09-01", "end": "2009-06-30"},
    {"name": "COVID-19 Pandemic", "start": "2020-02-01", "end": "2020-12-31"},
    {"name": "Russia-Ukraine War", "start": "2022-02-24", "end": "2022-12-31"},
]

# عمل عمود جديد لتحديد إذا التاريخ داخل أزمة
df["in_crisis"] = False
df["crisis_name"] = None

for p in periods:
    mask = (df["date"] >= p["start"]) & (df["date"] <= p["end"])
    df.loc[mask, "in_crisis"] = True
    df.loc[mask, "crisis_name"] = p["name"]


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
