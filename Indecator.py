# indicator_app.py
# Final, robust Streamlit app to compute GTI (Geopolitical Tension Index)
# - Requires: stocks_weights.csv and backup_weights.csv in the same folder
# - Optional: set Streamlit secrets:
#    GITHUB_TOKEN = "<personal access token>"
#    GITHUB_REPO  = "username/repo"   (e.g. "alparody/GeopoliticalTensionIndex")
#
# Usage: streamlit run indicator_app.py

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import base64
import requests
import os
import shutil
from datetime import date, timedelta

st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")
st.title("Geopolitical Tension Index (GTI) — Final")

# ---------- Config: filenames ----------
WEIGHTS_FILE = "stocks_weights.csv"
BACKUP_FILE = "backup_weights.csv"
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") if "GITHUB_TOKEN" in st.secrets else os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = st.secrets.get("GITHUB_REPO") if "GITHUB_REPO" in st.secrets else os.environ.get("GITHUB_REPO")


# ---------- Helpers ----------
def read_weights(path=WEIGHTS_FILE):
    if not os.path.exists(path):
        st.error(f"Weights file not found: {path}")
        st.stop()
    df = pd.read_csv(path)
    # normalize column names
    df.columns = [c.strip() for c in df.columns]
    # ensure required columns (symbol, weight, positive) exist
    # allow different cases
    cols_lower = {c.lower(): c for c in df.columns}
    if "symbol" not in cols_lower or "weight" not in cols_lower or "positive" not in cols_lower:
        st.error("Weights CSV must contain columns: symbol, weight, positive (case-insensitive).")
        st.stop()
    # rename to standard names to use below
    df = df.rename(columns={cols_lower["symbol"]:"symbol", cols_lower["weight"]:"weight", cols_lower["positive"]:"positive"})
    # optional full_name column
    if "full_name" not in df.columns:
        df["full_name"] = df["symbol"]
    # ensure types
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0.0)
    df["positive"] = df["positive"].astype(int)
    return df

def save_weights_local(df, path=WEIGHTS_FILE):
    df.to_csv(path, index=False)

def push_to_github(content_str, path_in_repo, commit_message="Update weights from Streamlit"):
    """Push file content to GitHub repo path using REST API (requires GITHUB_TOKEN & GITHUB_REPO)."""
    token = GITHUB_TOKEN
    repo = GITHUB_REPO
    if not token or not repo:
        return False, "GITHUB_TOKEN or GITHUB_REPO not configured in secrets"
    api_url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    # get current sha if exists
    r = requests.get(api_url, headers=headers)
    content_b64 = base64.b64encode(content_str.encode()).decode()
    if r.status_code == 200:
        sha = r.json().get("sha")
        payload = {"message": commit_message, "content": content_b64, "sha": sha}
    else:
        payload = {"message": commit_message, "content": content_b64}
    r2 = requests.put(api_url, headers=headers, json=payload)
    if r2.status_code in (200,201):
        return True, "OK"
    else:
        return False, f"GitHub API error: {r2.status_code} {r2.text}"

def get_price_data(symbols, start, end):
    """Download close prices robustly, return DataFrame with prices (columns are symbols)"""
    if not symbols:
        return pd.DataFrame()
    raw = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)
    # handle multiindex
    if isinstance(raw.columns, pd.MultiIndex):
        # try 'Close' level
        if "Close" in raw:
            data = raw["Close"]
        else:
            # if auto_adjust True, we might have single-level columns for tickers already
            data = raw
    else:
        data = raw
    if isinstance(data, pd.Series):
        data = data.to_frame()
    # drop columns that are all NaN
    data = data.dropna(how="all", axis=1)
    return data

def compute_gti_from_prices(prices, weights_df, ewma_span=10):
    """
    prices: DataFrame of price series (index dates, columns symbols)
    weights_df: DataFrame with columns symbol, weight, positive
    Returns: index_pct (0-100 scaled Series), index_raw (cumsum of weighted series)
    """
    # compute returns
    returns = prices.pct_change().dropna(how="all")
    if returns.empty:
        return None, None

    # EWMA smoothing on returns
    returns_ewma = returns.ewm(span=ewma_span, adjust=False).mean()

    # z-score normalization per column (avoid division by 0)
    z = (returns_ewma - returns_ewma.mean()) / returns_ewma.std(ddof=0)
    z = z.fillna(0.0)

    # align weights
    symbols_present = [s for s in weights_df["symbol"].tolist() if s in z.columns]
    if len(symbols_present) == 0:
        return None, None
    dfw = weights_df[weights_df["symbol"].isin(symbols_present)].copy()

    total_w = dfw["weight"].sum()
    if total_w == 0:
        total_w = 1.0

    weighted = pd.DataFrame(index=z.index)
    for _, r in dfw.iterrows():
        s = r["symbol"]
        sign = 1 if int(r["positive"]) == 1 else -1
        w_frac = (r["weight"] / total_w)
        weighted[s] = z[s] * w_frac * sign

    # penalty factor: penalize sudden negative moves (drawdown)
    # compute daily index changes before cumsum
    daily_contrib = weighted.sum(axis=1)
    # compute drawdown-like quick drop: when today's change < -2*std, amplify negative effect
    std_dev = daily_contrib.std()
    threshold = -2 * std_dev if std_dev > 0 else -1e9
    penalty = daily_contrib.apply(lambda x: x * 1.5 if x < threshold else 0.0)

    adjusted_daily = daily_contrib + penalty

    # cumulative index (start at 0)
    index_raw = adjusted_daily.cumsum()

    # scale 0-100
    min_v = index_raw.min()
    max_v = index_raw.max()
    if max_v == min_v:
        index_pct = pd.Series(50.0, index=index_raw.index)
    else:
        index_pct = (index_raw - min_v) / (max_v - min_v) * 100.0

    return index_pct, index_raw

def gti_color(val):
    try:
        v = float(val)
    except:
        return "gray"
    if v < 40:
        return "#2ecc71"  # green
    if v < 60:
        return "#f1c40f"  # yellow
    if v < 80:
        return "#e67e22"  # orange
    return "#e74c3c"      # red

# ---------- UI: Controls ----------
st.sidebar.header("Analysis Settings")
# date range
default_end = date.today()
default_start = default_end - timedelta(days=365)
start_date = st.sidebar.date_input("From Date", default_start)
end_date = st.sidebar.date_input("To Date", default_end)
if st.sidebar.button("Restore Default Dates"):
    start_date = default_start
    end_date = default_end
    st.experimental_rerun()

# chart type
chart_type = st.sidebar.selectbox("Chart Type", ["Line", "Bar"])

# EWMA span
ewma_span = st.sidebar.number_input("EWMA span (days)", min_value=1, max_value=60, value=10)

st.sidebar.markdown("---")
st.sidebar.markdown("**GitHub settings (optional)**")
st.sidebar.write("Set `GITHUB_TOKEN` and `GITHUB_REPO` in Streamlit Secrets or env variables to enable GitHub Save/Restore.")

# ---------- Main flow ----------
weights = read_weights(WEIGHTS_FILE)

# fetch price data
symbols = weights["symbol"].tolist()
with st.spinner("Fetching price data from Yahoo Finance..."):
    prices = get_price_data(symbols, start_date, end_date)

if prices is None or prices.empty:
    st.error("No price data available for the selected symbols / date range.")
    st.stop()

# compute GTI
index_pct, index_raw = compute_gti_from_prices(prices, weights, ewma_span=ewma_span)
if index_pct is None:
    st.error("GTI could not be computed (no overlapping symbols with price data).")
    st.stop()

# ---------- Display GTI value + colored square ----------
gti_today = float(index_pct.iloc[-1])
color_hex = gti_color(gti_today)

col1, col2 = st.columns([3,1])
with col1:
    st.markdown(f"### Today's GTI: **{gti_today:.2f}**")
with col2:
    st.markdown(f"<div style='width:40px;height:28px;border-radius:4px;background:{color_hex};'></div>", unsafe_allow_html=True)

st.markdown("---")

# ---------- Plot GTI only ----------
fig = go.Figure()
fig.add_trace(go.Scatter(x=index_pct.index, y=index_pct.values, mode="lines", name="GTI"))
fig.update_layout(title="Geopolitical Tension Index (0–100)", xaxis_title="Date", yaxis_title="GTI")
if chart_type == "Bar":
    # convert line to bar
    fig = go.Figure(go.Bar(x=index_pct.index, y=index_pct.values, name="GTI"))
    fig.update_layout(title="Geopolitical Tension Index (0–100)", xaxis_title="Date", yaxis_title="GTI")

st.plotly_chart(fig, use_container_width=True, theme="streamlit")

# ---------- Table BELOW chart + Buttons ----------
st.markdown("### Adjust Weights (edit below then Save Changes)")
col_table, col_buttons = st.columns([4,1])

# Use whichever editor exists
editor_func = getattr(st, "data_editor", None) or getattr(st, "experimental_data_editor", None) or None

with col_table:
    if editor_func:
        edited = editor_func(weights, num_rows="dynamic", use_container_width=True, key="weights_editor")
    else:
        st.write("Your Streamlit version doesn't support inline editing. Displaying table (not editable).")
        st.dataframe(weights, use_container_width=True)
        edited = weights.copy()

with col_buttons:
    if st.button("💾 Save Changes"):
        # save locally
        save_weights_local(edited, WEIGHTS_FILE)
        # try push to GitHub if configured
        try:
            csv_text = edited.to_csv(index=False)
            ok, msg = push_to_github(csv_text, WEIGHTS_FILE, commit_message="Update weights via app")
            if ok:
                st.success("Saved locally and pushed to GitHub.")
            else:
                st.warning(f"Saved locally. GitHub push skipped: {msg}")
        except Exception as e:
            st.warning(f"Saved locally. GitHub push attempt failed: {e}")
        st.experimental_rerun()

    if st.button("♻️ Restore Original (from backup)"):
        if not os.path.exists(BACKUP_FILE):
            st.error(f"Backup file not found: {BACKUP_FILE}")
        else:
            shutil.copy(BACKUP_FILE, WEIGHTS_FILE)
            # optionally push backup to github as restore
            # read backup content
            with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                csv_text = f.read()
            if GITHUB_TOKEN and GITHUB_REPO:
                ok, msg = push_to_github(csv_text, WEIGHTS_FILE, commit_message="Restore weights from backup via app")
                if ok:
                    st.success("Restored from backup and pushed to GitHub.")
                else:
                    st.warning(f"Restored locally. GitHub push failed: {msg}")
            else:
                st.success("Restored locally from backup.")
            st.experimental_rerun()

# ---------- Performance summary ----------
st.markdown("---")
st.subheader("Performance summary (GTI series)")
daily = index_pct.pct_change().dropna()
vol = daily.std()
sharpe_like = daily.mean() / vol if vol > 0 else np.nan
# correlation to VIX if available
corr_vix = np.nan
if "^VIX" in prices.columns:
    corr_vix = daily.corr(prices["^VIX"].pct_change().loc[daily.index])
corr_summary = {
    "Latest GTI": float(gti_today),
    "Volatility (daily, GTI)": float(vol) if not np.isnan(vol) else None,
    "Sharpe-like (GTI)": float(sharpe_like) if not np.isnan(sharpe_like) else None,
    "Corr (GTI vs VIX)": float(corr_vix) if not np.isnan(corr_vix) else None
}
st.json(corr_summary)
