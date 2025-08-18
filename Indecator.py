# indicator_app.py
# Streamlit app: Geopolitical Tension Index (GTI) - classic calculation, new interface

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
st.title("Geopolitical Tension Index (GTI) — Classic Calculation")

# ---------- Config ----------
WEIGHTS_FILE = "stocks_weights.csv"
BACKUP_FILE = "backup_weights.csv"
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") if "GITHUB_TOKEN" in st.secrets else os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = st.secrets.get("GITHUB_REPO") if "GITHUB_REPO" in st.secrets else os.environ.get("GITHUB_REPO")

# ---------- Helper functions ----------
def read_weights(path=WEIGHTS_FILE):
    if not os.path.exists(path):
        st.error(f"Weights file not found: {path}")
        st.stop()
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    cols_lower = {c.lower(): c for c in df.columns}
    if "symbol" not in cols_lower or "weight" not in cols_lower or "positive" not in cols_lower:
        st.error("Weights CSV must contain columns: symbol, weight, positive (case-insensitive).")
        st.stop()
    df = df.rename(columns={cols_lower["symbol"]:"symbol", cols_lower["weight"]:"weight", cols_lower["positive"]:"positive"})
    if "full_name" not in df.columns:
        df["full_name"] = df["symbol"]
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0.0)
    df["positive"] = df["positive"].astype(int)
    return df

def save_weights_local(df, path=WEIGHTS_FILE):
    df.to_csv(path, index=False)

def push_to_github(content_str, path_in_repo, commit_message="Update weights from Streamlit"):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GitHub token or repo not set"
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path_in_repo}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
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
    if not symbols:
        return pd.DataFrame()
    raw = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw:
            data = raw["Close"]
        else:
            data = raw
    else:
        data = raw
    if isinstance(data, pd.Series):
        data = data.to_frame()
    data = data.dropna(how="all", axis=1)
    return data

def compute_gti_classic(prices, weights_df):
    """Classic GTI: weighted sum of daily returns, cumulative, scale 0-100"""
    returns = prices.pct_change().fillna(0)
    symbols_present = [s for s in weights_df["symbol"].tolist() if s in returns.columns]
    if len(symbols_present) == 0:
        return None, None
    dfw = weights_df[weights_df["symbol"].isin(symbols_present)].copy()
    total_w = dfw["weight"].sum()
    if total_w == 0:
        total_w = 1.0
    weighted = pd.DataFrame(index=returns.index)
    for _, r in dfw.iterrows():
        s = r["symbol"]
        sign = 1 if int(r["positive"])==1 else -1
        weighted[s] = returns[s]*r["weight"]/total_w*sign
    index_raw = weighted.sum(axis=1).cumsum()
    # scale to 0-100
    min_v = index_raw.min()
    max_v = index_raw.max()
    if max_v == min_v:
        index_pct = pd.Series(50.0, index=index_raw.index)
    else:
        index_pct = (index_raw - min_v)/(max_v - min_v)*100.0
    return index_pct, index_raw

def gti_color(val):
    try:
        v = float(val)
    except:
        return "gray"
    if v < 40: return "#2ecc71"
    if v < 60: return "#f1c40f"
    if v < 80: return "#e67e22"
    return "#e74c3c"

# ---------- UI ----------
st.sidebar.header("Settings")
default_end = date.today()
default_start = default_end - timedelta(days=365)
start_date = st.sidebar.date_input("From Date", default_start)
end_date = st.sidebar.date_input("To Date", default_end)
if st.sidebar.button("Restore Default Dates"):
    start_date = default_start
    end_date = default_end
    st.experimental_rerun()

chart_type = st.sidebar.selectbox("Chart Type", ["Line", "Bar"])

# ---------- Main ----------
weights = read_weights()
symbols = weights["symbol"].tolist()
with st.spinner("Fetching price data..."):
    prices = get_price_data(symbols, start_date, end_date)
if prices.empty:
    st.error("No price data available.")
    st.stop()

index_pct, index_raw = compute_gti_classic(prices, weights)
if index_pct is None:
    st.error("GTI could not be computed.")
    st.stop()

# ---------- Display GTI value ----------
gti_today = float(index_pct.iloc[-1])
color_hex = gti_color(gti_today)
col1, col2 = st.columns([3,1])
with col1:
    st.markdown(f"### Today's GTI: **{gti_today:.2f}**")
with col2:
    st.markdown(f"<div style='width:40px;height:28px;border-radius:4px;background:{color_hex};'></div>", unsafe_allow_html=True)

st.markdown("---")

# ---------- Plot GTI ----------
fig = go.Figure()
if chart_type=="Line":
    fig.add_trace(go.Scatter(x=index_raw.index, y=index_raw.values, mode="lines", name="GTI"))
else:
    fig.add_trace(go.Bar(x=index_raw.index, y=index_raw.values, name="GTI"))
fig.update_layout(title="Geopolitical Tension Index (0–100)", xaxis_title="Date", yaxis_title="GTI", yaxis=dict(range=[0,100]))
st.plotly_chart(fig, use_container_width=True)

# ---------- Table below chart + buttons ----------
st.markdown("### Adjust Weights")
col_table, col_buttons = st.columns([4,1])
editor_func = getattr(st, "data_editor", None) or getattr(st, "experimental_data_editor", None) or None

with col_table:
    if editor_func:
        edited = editor_func(weights, num_rows="dynamic", use_container_width=True, key="weights_editor")
    else:
        st.dataframe(weights, use_container_width=True)
        edited = weights.copy()

with col_buttons:
    if st.button("💾 Save Changes"):
        save_weights_local(edited)
        try:
            csv_text = edited.to_csv(index=False)
            ok,msg = push_to_github(csv_text, WEIGHTS_FILE)
            if ok:
                st.success("Saved locally and pushed to GitHub.")
            else:
                st.warning(f"Saved locally. GitHub push failed: {msg}")
        except:
            st.warning("Saved locally. GitHub push attempt failed.")
        st.experimental_rerun()
    if st.button("♻️ Restore Original (from backup)"):
        if os.path.exists(BACKUP_FILE):
            shutil.copy(BACKUP_FILE, WEIGHTS_FILE)
            st.success("Restored from backup locally.")
            st.experimental_rerun()
        else:
            st.error("Backup file not found.")

# ---------- Performance summary ----------
st.markdown("---")
st.subheader("Performance Summary")
daily = index_pct.pct_change().dropna()
vol = daily.std()
sharpe_like = daily.mean()/vol if vol>0 else np.nan
corr_vix = daily.corr(prices["^VIX"].pct_change().loc[daily.index]) if "^VIX" in prices.columns else np.nan
st.json({
    "Latest GTI": float(gti_today),
    "Volatility (daily, GTI)": float(vol) if not np.isnan(vol) else None,
    "Sharpe-like (GTI)": float(sharpe_like) if not np.isnan(sharpe_like) else None,
    "Corr (GTI vs VIX)": float(corr_vix) if not np.isnan(corr_vix) else None
})
