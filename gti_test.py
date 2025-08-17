import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime

import statsmodels.api as sm
from statsmodels.tsa.stattools import grangercausalitytests

# ---------------------------------------------------
# دالة لاختبار السببية
# ---------------------------------------------------
def run_causality_test(data: pd.DataFrame, maxlag: int = 5):
    """
    Run Granger Causality Test between GTI and other assets (VIX, Gold).
    data: DataFrame يحتوي الأعمدة [GTI, ^VIX, GC=F]
    maxlag: عدد الـ lags
    """
    results = []

    for target in ["^VIX", "GC=F"]:
        # causality: Does GTI -> target ?
        test1 = grangercausalitytests(data[["GTI", target]], maxlag=maxlag, verbose=False)
        p_values1 = [round(test1[i+1][0]['ssr_ftest'][1], 4) for i in range(maxlag)]
        min_pval1 = min(p_values1)

        # reverse causality: Does target -> GTI ?
        test2 = grangercausalitytests(data[[target, "GTI"]], maxlag=maxlag, verbose=False)
        p_values2 = [round(test2[i+1][0]['ssr_ftest'][1], 4) for i in range(maxlag)]
        min_pval2 = min(p_values2)

        results.append({
            "Target": target,
            "GTI → " + target: min_pval1,
            target + " → GTI": min_pval2
        })

    return pd.DataFrame(results)


# ---------------------------------------------------
# داخل الدالة الرئيسية بعد حساب correlations
# ---------------------------------------------------
    st.subheader("Causality Test (Granger)")

    try:
        causality_df = run_causality_test(combined, maxlag=5)
        st.dataframe(causality_df, use_container_width=True)

        st.info("ملاحظة: قيم P-Value < 0.05 تعني وجود سببية ذات دلالة إحصائية.")
    except Exception as e:
        st.error(f"Causality test failed: {e}")

# --- Default event periods (name: (start, end)) ---
DEFAULT_PERIODS = {
    "Russia-Ukraine invasion (early)": ("2022-02-24", "2022-05-31"),
    "Israel-Hamas (Oct 2023)": ("2023-10-07", "2023-12-15"),
    "Global market shock (Mar 2020)": ("2020-02-15", "2020-05-31"),
}

# --- Helper functions ---
def safe_download(symbols, start, end):
    """Download prices (auto_adjust) and return Close dataframe (or None)."""
    raw = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return None
    # handle MultiIndex or single
    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw:
            data = raw["Close"]
        else:
            data = raw.iloc[:, raw.shape[1]//2 : raw.shape[1]//2 + len(symbols)]
    else:
        if "Close" in raw:
            data = raw["Close"]
        else:
            data = raw
    if isinstance(data, pd.Series):
        data = data.to_frame()
    return data

def max_drawdown(series):
    roll_max = series.cummax()
    drawdown = (series - roll_max) / roll_max
    return drawdown.min()

def compute_stats(index_series):
    returns = index_series.pct_change().dropna()
    stats = {
        "mean_daily_return": returns.mean(),
        "volatility_daily": returns.std(),
        "start_value": float(index_series.iloc[0]),
        "end_value": float(index_series.iloc[-1]),
        "max_value": float(index_series.max()),
        "min_value": float(index_series.min()),
        "max_drawdown": float(max_drawdown(index_series)),
    }
    return stats, returns

# --- Main function ---
def run_gti_test(periods=None, lookback_months=6):
    try:
        periods = periods or DEFAULT_PERIODS

        # 1) load weights
        weights_file = "stocks_weights.csv"
        df = pd.read_csv(weights_file)
        df = df.rename(columns={c: c.strip() for c in df.columns})

        if not {"symbol", "weight", "positive"}.issubset(set(df.columns)):
            st.error("CSV must contain columns: symbol, weight, positive")
            return

        df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
        df["positive"] = df["positive"].astype(int)
        df = df.dropna(subset=["weight"])
        original_symbols = df["symbol"].tolist()

        st.write("### GTI Test — configuration")
        st.write(f"Loaded {len(df)} symbols from `{weights_file}`")
        st.write(df)

        # Always fetch VIX and Gold for comparison
        bench_symbols = ["^VIX", "GC=F"]
        fetch_symbols = sorted(set(original_symbols + bench_symbols))

        # pre-download full period
        starts = [pd.to_datetime(s[0]) for s in periods.values()]
        ends = [pd.to_datetime(s[1]) for s in periods.values()]
        global_start = min(starts) - pd.Timedelta(days=7)
        global_end = max(ends) + pd.Timedelta(days=1)

        with st.spinner(f"Downloading {len(fetch_symbols)} symbols from {global_start.date()} to {global_end.date()} ..."):
            data = safe_download(fetch_symbols, global_start.strftime("%Y-%m-%d"), global_end.strftime("%Y-%m-%d"))

        if data is None or data.empty:
            st.error("No price data returned from Yahoo Finance. Check symbols or network.")
            return

        data = data.dropna(how="all").ffill().bfill()

        available = [c for c in data.columns if c in fetch_symbols]
        missing = sorted(set(fetch_symbols) - set(available))
        if missing:
            st.warning(f"Missing symbols (no data) and will be excluded: {', '.join(missing)}")

        available_original = [s for s in original_symbols if s in available]
        if not available_original:
            st.error("No overlap between CSV symbols and fetched data.")
            return

        df = df[df["symbol"].isin(available_original)].copy()
        returns = data[available].pct_change(fill_method=None).dropna(how="all").ffill().bfill()

        # signed normalized weights
        w = df.set_index("symbol")["weight"]
        w = w / w.sum()
        sign = df.set_index("symbol")["positive"].map(lambda x: 1 if int(x) == 1 else -1)
        signed_w = (w * sign).reindex(returns.columns).fillna(0)

        # GTI returns/index
        gti_ret = (returns * signed_w).sum(axis=1)
        gti_index = 100 * (1 + gti_ret).cumprod()

        rows = []

        st.write("### Results by period")
        for name, (start_str, end_str) in periods.items():
            start = pd.to_datetime(start_str)
            end = pd.to_datetime(end_str)
            mask = (gti_index.index >= start) & (gti_index.index <= end)
            if mask.sum() < 2:
                st.warning(f"Period {name} has insufficient data ({mask.sum()} points). Skipping.")
                continue

            gti_period = gti_index.loc[mask].dropna()
            stats, gti_returns = compute_stats(gti_period)

            correlations = {}
            for bench in bench_symbols:
                if bench in returns.columns:
                    bench_ret = returns.loc[mask, bench].dropna()
                    joined = pd.concat([gti_returns, bench_ret.reindex(gti_returns.index)], axis=1).dropna()
                    if not joined.empty:
                        correlations[f"corr_with_{bench}"] = joined.iloc[:, 0].corr(joined.iloc[:, 1])
                    else:
                        correlations[f"corr_with_{bench}"] = np.nan
                else:
                    correlations[f"corr_with_{bench}"] = np.nan

            row = {
                "period": name,
                "start": start_str,
                "end": end_str,
                **{k: float(v) for k, v in stats.items()},
                **correlations
            }
            rows.append(row)

            st.write(f"#### {name} — {start_str} → {end_str}")
            fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})

            gti_period.plot(ax=ax[0], label="GTI (index)", linewidth=2)

            if "^GSPC" in data.columns:
                sp = 100 * data["^GSPC"].loc[start:end] / data["^GSPC"].loc[start:end].iloc[0]
                sp.plot(ax=ax[0], label="S&P500 (norm)", alpha=0.8)
            if "^VIX" in data.columns:
                vix = 100 * data["^VIX"].loc[start:end] / data["^VIX"].loc[start:end].iloc[0]
                vix.plot(ax=ax[0], label="VIX (norm)", alpha=0.8)
            if "GC=F" in data.columns:
                gold = 100 * data["GC=F"].loc[start:end] / data["GC=F"].loc[start:end].iloc[0]
                gold.plot(ax=ax[0], label="Gold (norm)", alpha=0.8)

            ax[0].legend()
            ax[0].set_ylabel("Index / Normalized Price")

            last_ret = returns.loc[start:end].iloc[-1]
            contrib = (last_ret * signed_w.reindex(last_ret.index).fillna(0)).sort_values()
            contrib.plot(kind="barh", ax=ax[1])
            ax[1].set_xlabel("Today's weighted contribution (signed)")

            st.pyplot(fig)

        if rows:
            summary_df = pd.DataFrame(rows)
            st.write("### Summary statistics across tested periods")
            st.dataframe(summary_df.style.format({
                "mean_daily_return": "{:.6f}",
                "volatility_daily": "{:.6f}",
                "max_drawdown": "{:.4f}",
                "corr_with_^VIX": "{:.4f}",
                "corr_with_GC=F": "{:.4f}"
            }), use_container_width=True)

            st.download_button(
                label="Download test summary (CSV)",
                data=summary_df.to_csv(index=False).encode("utf-8"),
                file_name="gti_test_summary.csv",
                mime="text/csv"
            )
        else:
            st.info("No valid periods were tested (insufficient data or periods skipped).")

    except Exception as e:
        st.error(f"Error running GTI full test: {e}")
