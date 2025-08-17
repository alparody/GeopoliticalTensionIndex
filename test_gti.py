import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# 1- قراءة ملف CSV
weights_df = pd.read_csv("gti_weights.csv")

# 2- تنزيل البيانات التاريخية
symbols = weights_df["symbol"].tolist()
data = yf.download(symbols, start="2022-01-01", end="2025-01-01")["Adj Close"]

# 3- معالجة: ملء الفراغات
data = data.fillna(method="ffill").fillna(method="bfill")

# 4- حساب العائد اليومي لكل أصل
returns = data.pct_change().fillna(0)

# 5- دمج مع الأوزان
gti_series = pd.Series(0, index=returns.index)

for _, row in weights_df.iterrows():
    symbol, weight, positive = row["symbol"], row["weight"], row["positive"]

    # تعديل الاتجاه: لو positive=0 يبقى سلبي (معكوس)
    factor = 1 if positive == 1 else -1

    gti_series += weight * factor * returns[symbol]

# 6- تطبيع (Normalization) علشان يبقى في Range معقول
gti_index = (1 + gti_series.cumsum())
gti_index = 100 * (gti_index / gti_index.iloc[0])  # يبدأ من 100

# 7- مقارنة مع مؤشرات مرجعية (مثلاً S&P 500 و VIX)
ref_symbols = ["^GSPC", "^VIX"]
ref_data = yf.download(ref_symbols, start="2022-01-01", end="2025-01-01")["Adj Close"]
ref_data = ref_data.fillna(method="ffill").fillna(method="bfill")
ref_data = 100 * ref_data / ref_data.iloc[0]  # تطبيع برضه يبدأ من 100

# 8- رسم النتيجة
plt.figure(figsize=(12, 6))
plt.plot(gti_index, label="Geopolitical Tension Index (GTI)", linewidth=2)
plt.plot(ref_data["^GSPC"], label="S&P 500 (normalized)", alpha=0.7)
plt.plot(ref_data["^VIX"], label="VIX (normalized)", alpha=0.7)
plt.legend()
plt.title("Testing GTI vs S&P 500 and VIX")
plt.show()
