def run_gti_test():
    from data_loader import load_stock_data
    import pandas as pd

    # تحميل البيانات
    df = load_stock_data()

    # أمثلة على أكثر من مقترح للأوزان
    weight_scenarios = [
        {"AAPL": 0.3, "MSFT": 0.3, "GOOG": 0.4},
        {"AAPL": 0.25, "MSFT": 0.25, "GOOG": 0.25, "META": 0.25},
        {"AAPL": 0.5, "MSFT": 0.3, "GOOG": 0.2},
    ]

    results = []

    for i, weights in enumerate(weight_scenarios, 1):
        print(f"\nRunning Scenario {i} with weights: {weights}")
        print("Available columns in df:", df.columns.tolist())  # 👈 تتأكد الأعمدة
        
        missing = [t for t in weights if t not in df.columns]
        if missing:
            print(f"⚠️ Missing columns for Scenario {i}: {missing}")
            continue

        # احسب المؤشر
        df[f"GTI_{i}"] = sum(df[ticker] * weight for ticker, weight in weights.items())

        results.append(df[[f"GTI_{i}"]])

    # لو فيه نتائج
    if results:
        final = pd.concat(results, axis=1)
        print("\n✅ Final GTI Results:")
        print(final.head())
    else:
        print("❌ No scenarios could be calculated because of missing columns.")
