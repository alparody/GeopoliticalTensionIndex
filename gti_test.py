import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import streamlit as st

def run_gti_test():
    try:
        # 1) Load weights
        df = pd.read_csv("stocks_weights.csv")
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
        df["positive"] = df["positive"].astype(int)
        df = df.dropna(subset=["weight"])
        symbols = df["symbol"].tolist()

        st.write("### 📊 GTI Test Run")
        st.write("Using weights file with symbols:", symbols)

        # 2) Download prices (auto_adjust=True ⇒ نستخدم Close)
        raw = yf.download(
            symbols,
            period="6mo",
            auto_adjust=True,
            progress=False,
        )

        if raw is None or raw.empty:
            st.error("No price data returned from Yahoo Finance.")
            return

        # Extract Close robustly (handles MultiIndex or single series)
        if isinstance(raw.columns, pd.MultiIndex):
            data = raw["Close"]
        else:
            # Single-ticker case may be a DataFrame with 'Close' or just a Series
            data = raw["Close"] if "Close" in raw else raw

        # Ensure DataFrame shape
        if isinstance(data, pd.Series):
            data = data.to_frame()

        # 3) Clean & align
        data = data.dropna(how="all").ffill().bfill()
        available_cols = [c for c in data.columns if c in symbols]
        missing = sorted(set(symbols) - set(available_cols))
        if missing:
            st.warning(
                f"Excluded {len(missing)} symbol(s) with no data: {', '.join(missing)}"
            )
        # Align df & data to available symbols only
        df = df[df["symbol"].isin(available_cols)].copy()
        data = data[available_cols]

        if df.empty or data.empty:
            st.error("No overlapping symbols between CSV and fetched data.")
            return

        # 4) Daily returns
        returns = data.pct_change(fill_method=None).dropna(how="all")
        if returns.empty:
            st.error("No returns could be computed (not enough data).")
            return

        # 5) Build signed, normalized weights aligned to returns columns
        w = df.set_index("symbol")["weight"]
        w = w / w.sum()  # normalize to 1
        sign = df.set_index("symbol")["positive"].map(lambda x: 1 if int(x) == 1 else -1)
        signed_w = (w * sign).reindex(returns.columns).fillna(0)

        # 6) Weighted daily return & GTI index starting at 100
        gti_ret = (returns * signed_w).sum(axis=1)
        gti_index = 100 * (1 + gti_ret).cumprod()

        # 7) Benchmarks (normalized to 100)
        ref_raw = yf.download(
            ["^VIX", "^GSPC"], period="6mo", auto_adjust=True, progress=False
        )
        refs_norm = None
        if ref_raw is not None and not ref_raw.empty:
            if isinstance(ref_raw.columns, pd.MultiIndex):
                refs = ref_raw["Close"].ffill().bfill()
            else:
                refs = ref_raw["Close"] if "Close" in ref_raw else ref_raw
            if isinstance(refs, pd.Series):
                refs = refs.to_frame()
            refs = refs.ffill().bfill()
            refs_norm = 100 * refs / refs.iloc[0]

        # 8) Plot
        fig, ax = plt.subplots(figsize=(10, 4))
        gti_index.plot(ax=ax, label="GTI (test)")
        if refs_norm is not None:
            if "^GSPC" in refs_norm.columns:
                refs_norm["^GSPC"].plot(ax=ax, alpha=0.6, label="S&P 500 (norm)")
            if "^VIX" in refs_norm.columns:
                refs_norm["^VIX"].plot(ax=ax, alpha=0.6, label="VIX (norm)")
        ax.set_title("GTI Test vs Benchmarks")
        ax.legend()
        st.pyplot(fig)

        # 9) Show today's weighted contributions
        last_contrib = (returns.iloc[-1] * signed_w).sort_values()
        st.write("### Today's Contributions (weighted)")
        st.dataframe(
            last_contrib.to_frame("contribution").style.format("{:.4f}"),
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"⚠️ Error running GTI test: {e}")
