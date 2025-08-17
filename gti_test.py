import pandas as pd
from data_loader import load_stock_data

def run_gti_test():
    # تحميل البيانات
    raw_data = load_stock_data()
    data = raw_data.copy()

    # نفترض إننا عندنا الأعمدة: ORHD, OCDI, VIX ...
    # لو في أي سهم ناقص هيتم تجاهله
    data = data.dropna(axis=1, how="all")

    # تعريف أكثر من سيناريو للأوزان النسبية
    weight_scenarios = {
        "Scenario 1": {"ORHD": 0.4, "OCDI": 0.4, "VIX": 0.2},
        "Scenario 2": {"ORHD": 0.5, "OCDI": 0.3, "VIX": 0.2},
        "Scenario 3": {"ORHD": 0.3, "OCDI": 0.5, "VIX": 0.2},
        "Scenario 4": {"ORHD": 0.33, "OCDI": 0.33, "VIX": 0.34}
    }

    results = []

    for scenario, weights in weight_scenarios.items():
        # نطبع بس الأعمدة اللي ليها وزن
        valid_cols = [col for col in weights.keys() if col in data.columns]
        temp = data[valid_cols].pct_change().dropna()

        # حساب المؤشر
        weighted_index = sum(temp[col] * weights[col] for col in valid_cols)
        avg_return = weighted_index.mean()
        volatility = weighted_index.std()

        results.append({
            "Scenario": scenario,
            "Avg_Return": avg_return,
            "Volatility": volatility
        })

    results_df = pd.DataFrame(results)

    print("\n📊 نتائج المقارنة بين السيناريوهات:")
    print(results_df)

    return results_df

if __name__ == "__main__":
    run_gti_test()
