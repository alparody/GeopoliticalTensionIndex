# indicator_app_final2.py
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import os
import shutil
import base64
import requests
from datetime import date, timedelta

st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")
st.title("Geopolitical Tension Index (0–100 Scale)")

# ---------- Config ----------
WEIGHTS_FILE = "stocks_weights.csv"
BACKUP_FILE = "backup_weights.csv"
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") if "GITHUB_TOKEN" in st.secrets else os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = st.secrets.get("GITHUB_REPO") if "GITHUB_REPO" in st.secrets else os.environ.get("GITHUB_REPO")

# ---------- Helper Functions ----------
def read_weights(path=WEIGHTS_FILE):
    if not os.path.exists(path):
        st.error(f"Weights file not found: {path}")
        st.stop()
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    for col in ["weight", "positive"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "full_name" not in df.columns:
        df["full_name"] = df["symbol"]
    return df

def save_weights_local(df, path=WEIGHTS_FILE):
    df.to_csv(path, index=False)

def push_to_github(content_str, path_in_repo, commit_message="Update weights"):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GitHub token or repo not set"
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path_in_repo}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(api_url, headers=headers)
    content_b64 = base64.b64encode(content_str.encode()).decode()
    payload = {"message": commit_message, "content": content_b64}
    if r.status_code == 200:
        sha = r.json().get("sha")
        payload["sha"] = sha
    r2 = requests.put(api_url, headers=headers, json=payload)
    if r2.status_code in (200,201):
        return True, "OK"
    else:
        return False, f"GitHub API error: {r2.status_code}"

@st.cache_data
def get_data(symbols, start, end):
    data = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex) and "Close" in data:
        data = data["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame()
    return data.dropna(how="all", axis=1)

def compute_gti(prices, weights_df):
    returns = prices.pct_change().fillna(0)
    symbols_present = [s for s in weights_df["symbol"] if s in returns.columns]
    dfw = weights_df[weights_df["symbol"].isin(symbols_present)]
    total_w = dfw["weight"].sum() or 1.0
    weighted = pd.DataFrame(index=returns.index)
    for _, r in dfw.iterrows():
        sign = 1 if int(r["positive"])==1 else -1
        weighted[r["symbol"]] = returns[r["symbol"]] * r["weight"]/total_w * sign
    index_raw = weighted.sum(axis=1).cumsum()
    min_v, max_v = index_raw.min(), index_raw.max()
    index_pct = (index_raw - min_v)/(max_v - min_v)*100 if max_v != min_v else pd.Series(50.0, index=index_raw.index)
    return index_pct, index_raw, weighted

def gti_color(val):
    if val < 40: return "#2ecc71"
    if val < 60: return "#f1c40f"
    if val < 80: return "#e67e22"
    return "#e74c3c"

# ---------- Sidebar Controls ----------
st.sidebar.header("Analysis Settings")
# Date inputs
default_end = date.today()
default_start = default_end - timedelta(days=365)
start_date = st.sidebar.date_input("From", default_start)
end_date = st.sidebar.date_input("To", default_end)
today_date = st.sidebar.date_input("Today", default_end)

chart_type = st.sidebar.selectbox("Chart Type", ["Line", "Bar"])

if st.sidebar.button("Restore Default Dates"):
    start_date, end_date, today_date = default_start, default_end, default_end
    st.experimental_rerun()

# ---------- Load Weights ----------
weights = read_weights()

# ---------- Fetch Data ----------
with st.spinner("Fetching price data..."):
    prices = get_data(weights["symbol"].tolist(), start_date, end_date)
if prices.empty:
    st.error("No price data available.")
    st.stop()

# ---------- Compute GTI ----------
index_pct, index_raw, weighted = compute_gti(prices, weights)
today_pct = float(index_pct.iloc[-1])
color_hex = gti_color(today_pct)

col1, col2 = st.columns([3,1])
with col1:
    st.markdown(f"### Today's GTI: **{today_pct:.2f}**")
with col2:
    st.markdown(f"<div style='width:40px;height:28px;border-radius:4px;background:{color_hex};'></div>", unsafe_allow_html=True)

st.markdown("---")

# ---------- Plot GTI ----------
fig = go.Figure()
if chart_type == "Line":
    fig.add_trace(go.Scatter(x=index_raw.index, y=index_pct.values, mode="lines+markers", name="GTI"))
else:
    fig.add_trace(go.Bar(x=index_raw.index, y=index_pct.values, name="GTI"))
fig.update_layout(title="Geopolitical Tension Index (0–100)", xaxis_title="Date", yaxis=dict(title="GTI", range=[0,100]))
st.plotly_chart(fig, use_container_width=True)

# ---------- Table & Buttons ----------
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

# ---------- Download ----------
st.download_button("Download Index Data (0–100)", index_pct.to_csv().encode("utf-8"), "geopolitical_index.csv", "text/csv")
