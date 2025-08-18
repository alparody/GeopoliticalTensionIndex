# indicator_app.py
# Final Streamlit app to compute GTI (Geopolitical Tension Index)
# Requires: stocks_weights.csv + backup_weights.csv in same folder

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import base64, requests, os, shutil
from datetime import date, timedelta

st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")
st.title("Geopolitical Tension Index (GTI)")

# ---------- Config ----------
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
    df.columns = [c.strip() for c in df.columns]
    cols_lower = {c.lower(): c for c in df.columns}
    if "symbol" not in cols_lower or "weight" not in cols_lower or "positive" not in cols_lower:
        st.error("Weights CSV must contain: symbol, weight, positive")
        st.stop()
    df = df.rename(columns={
        cols_lower["symbol"]: "symbol",
        cols_lower["weight"]: "weight",
        cols_lower["positive"]: "positive"
    })
    if "full_name" not in df.columns:
        df["full_name"] = df["symbol"]
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0.0)
    df["positive"] = df["positive"].astype(int)
    return df

def save_weights_local(df, path=WEIGHTS_FILE):
    df.to_csv(path, index=False)

def push_to_github(content_str, path_in_repo, commit_message="Update weights from Streamlit"):
    token, repo = GITHUB_TOKEN, GITHUB_REPO
    if not token or not repo:
        return False, "GITHUB_TOKEN or GITHUB_REPO missing"
    api_url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(api_url, headers=headers)
    content_b64 = base64.b64encode(content_str.encode()).decode()
    if r.status_code == 200:
        sha = r.json().get("sha")
        payload = {"message": commit_message, "content": content_b64, "sha": sha}
    else:
        payload = {"message": commit_message, "content": content_b64}
    r2 = requests.put(api_url, headers=headers, json=payload)
    return (r2.status_code in (200,201)), r2.text

def get_price_data(symbols, start, end):
    if not symbols:
        return pd.DataFrame()
    raw = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        data = raw["Close"] if "Close" in raw else raw
    else:
        data = raw
    if isinstance(data, pd.Series):
        data = data.to_frame()
    return data.dropna(how="all", axis=1)

def compute_gti(prices, weights_df, ewma_span=10):
    returns = prices.pct_change().dropna(how="all")
    if returns.empty:
        return None, None
    returns_ewma = returns.ewm(span=ewma_span, adjust=False).mean()
    z = (returns_ewma - returns_ewma.mean()) / returns_ewma.std(ddof=0)
    z = z.fillna(0.0)

    symbols_present = [s for s in weights_df["symbol"] if s in z.columns]
    if not symbols_present:
        return None, None
    dfw = weights_df[weights_df["symbol"].isin(symbols_present)].copy()
    total_w = dfw["weight"].sum() or 1.0

    weighted = pd.Series(0.0, index=z.index)
    for _, r in dfw.iterrows():
        sign = 1 if r["positive"] == 1 else -1
        weighted += z[r["symbol"]] * (r["weight"]/total_w) * sign

    # adjust for drawdowns
    std_dev = weighted.std()
    thr = -2*std_dev if std_dev > 0 else -1e9
    penalty = weighted.apply(lambda x: x*1.5 if x < thr else 0)
    adjusted = weighted + penalty
    index_raw = adjusted.cumsum()

    if index_raw.max() == index_raw.min():
        index_pct = pd.Series(50.0, index=index_raw.index)
    else:
        index_pct = (index_raw - index_raw.min())/(index_raw.max()-index_raw.min())*100
    return index_pct, index_raw

def gti_color(val):
    v = float(val)
    if v < 40: return "#2ecc71"
    if v < 60: return "#f1c40f"
    if v < 80: return "#e67e22"
    return "#e74c3c"

# ---------- Sidebar ----------
st.sidebar.header("Settings")
default_end, default_start = date.today(), date.today()-timedelta(days=365)
start_date = st.sidebar.date_input("From", default_start)
end_date = st.sidebar.date_input("To", default_end)
chart_type = st.sidebar.selectbox("Chart Type", ["Line", "Bar"])
ewma_span = st.sidebar.number_input("EWMA span (days)", 1, 60, 10)

# ---------- Main ----------
weights = read_weights()
symbols = weights["symbol"].tolist()
with st.spinner("Fetching price data..."):
    prices = get_price_data(symbols, start_date, end_date)

if prices is None or prices.empty:
    st.error("No price data available")
    st.stop()

index_pct, index_raw = compute_gti(prices, weights, ewma_span)
if index_pct is None:
    st.error("GTI could not be computed")
    st.stop()

gti_today = float(index_pct.iloc[-1])
color_hex = gti_color(gti_today)

col1,col2 = st.columns([3,1])
col1.markdown(f"### Today's GTI: **{gti_today:.2f}**")
col2.markdown(f"<div style='width:40px;height:28px;border-radius:4px;background:{color_hex}'></div>", unsafe_allow_html=True)

st.markdown("---")
fig = go.Figure()
if chart_type=="Line":
    fig.add_trace(go.Scatter(x=index_pct.index,y=index_pct.values,mode="lines",name="GTI"))
else:
    fig.add_trace(go.Bar(x=index_pct.index,y=index_pct.values,name="GTI"))
fig.update_layout(title="Geopolitical Tension Index (0–100)", xaxis_title="Date", yaxis_title="GTI")
st.plotly_chart(fig, use_container_width=True, theme="streamlit")

# ---------- Weights Editor ----------
st.markdown("### Adjust Weights")
editor = getattr(st, "data_editor", None) or getattr(st, "experimental_data_editor", None)
edited = editor(weights, num_rows="dynamic") if editor else weights
col_a,col_b = st.columns([4,1])
with col_b:
    if st.button("💾 Save Changes"):
        save_weights_local(edited, WEIGHTS_FILE)
        try:
            csv_text = edited.to_csv(index=False)
            ok,msg = push_to_github(csv_text, WEIGHTS_FILE, "Update weights via app")
            st.success("Saved + pushed" if ok else f"Saved locally only ({msg})")
        except Exception as e:
            st.warning(f"Saved locally, GitHub push failed: {e}")
        st.experimental_rerun()
    if st.button("♻️ Restore Backup"):
        if os.path.exists(BACKUP_FILE):
            shutil.copy(BACKUP_FILE, WEIGHTS_FILE)
            st.success("Restored backup")
            st.experimental_rerun()
        else:
            st.error("Backup file not found")

# ---------- Summary ----------
st.markdown("---")
st.subheader("Performance Summary")
daily = index_pct.pct_change().dropna()
vol = daily.std()
sharpe_like = daily.mean()/vol if vol>0 else np.nan
summary = {
    "Latest GTI": gti_today,
    "Volatility": float(vol) if vol>0 else None,
    "Sharpe-like": float(sharpe_like) if not np.isnan(sharpe_like) else None
}
st.json(summary)
