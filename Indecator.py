# indicator_app_final.py
import streamlit as st
import pandas as pd
import yfinance as yf
import os
import shutil
import requests
import base64
from datetime import date, timedelta
import altair as alt

st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")
st.title("Geopolitical Tension Index (GTI)")

# ---------- Config ----------
WEIGHTS_FILE = "stocks_weights.csv"
BACKUP_FILE = "backup_weights.csv"
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") if "GITHUB_TOKEN" in st.secrets else os.environ.get("GITHUB_TOKEN")
GITHUB_REPO  = st.secrets.get("GITHUB_REPO")  if "GITHUB_REPO"  in st.secrets else os.environ.get("GITHUB_REPO")

# ---------- Helpers ----------
def read_weights(path=WEIGHTS_FILE):
    if not os.path.exists(path):
        st.error(f"Weights file not found: {path}")
        st.stop()
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    # ensure required columns
    cols_lower = {c.lower(): c for c in df.columns}
    for col in ["symbol","weight","positive"]:
        if col not in cols_lower:
            st.error(f"Column '{col}' missing in CSV.")
            st.stop()
    df = df.rename(columns={cols_lower["symbol"]:"symbol", 
                            cols_lower["weight"]:"weight", 
                            cols_lower["positive"]:"positive"})
    if "full_name" not in df.columns:
        df["full_name"] = df["symbol"]
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0.0)
    df["positive"] = df["positive"].astype(int)
    return df

def save_weights_local(df, path=WEIGHTS_FILE):
    df.to_csv(path, index=False)

def push_to_github(content_str, path_in_repo, commit_message="Update weights"):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GitHub token or repo not configured"
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
    return False, f"GitHub API error: {r2.status_code} {r2.text}"

@st.cache_data(show_spinner=False)
def get_price_data(symbols, start, end):
    raw = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)["Close"].dropna(how="all", axis=1)
    return raw

def gti_color(val):
    try: v = float(val)
    except: return "gray"
    if v<40: return "#2ecc71"
    if v<60: return "#f1c40f"
    if v<80: return "#e67e22"
    return "#e74c3c"

# ---------- Sidebar ----------
st.sidebar.header("Analysis Settings")
default_end = date.today()
default_start = default_end - timedelta(days=365)

# Initialize session_state
for k, v in [("start_date", default_start), ("end_date", default_end), ("today_date", default_end)]:
    if k not in st.session_state:
        st.session_state[k] = v

# Sidebar inputs
start_date = st.sidebar.date_input("From Date", st.session_state.start_date, key="start_input")
end_date   = st.sidebar.date_input("To Date", st.session_state.end_date, key="end_input")
today_date = st.sidebar.date_input("Today", st.session_state.today_date, key="today_input")

# Restore defaults function
def restore_defaults():
    st.session_state.start_date = default_start
    st.session_state.end_date   = default_end
    st.session_state.today_date = default_end

st.sidebar.button("Restore Default Dates", on_click=restore_defaults)

# ---------- Main ----------
weights = read_weights(WEIGHTS_FILE)
symbols = weights["symbol"].tolist()

with st.spinner("Fetching price data..."):
    prices = get_price_data(symbols, st.session_state.start_date, st.session_state.end_date)

if prices is None or prices.empty:
    st.error("No price data available.")
    st.stop()

# --- Compute weighted cumulative GTI ---
returns = prices.pct_change().dropna(how="all")
available = [s for s in symbols if s in returns.columns]
weights = weights[weights["symbol"].isin(available)].copy()
returns = returns[available]

total_weight = weights["weight"].sum()
weighted = pd.DataFrame(index=returns.index)
for _, row in weights.iterrows():
    sign = 1 if int(row["positive"])==1 else -1
    weighted[row["symbol"]] = returns[row["symbol"]] * (row["weight"]/total_weight) * sign

index_series = weighted.sum(axis=1).cumsum()
min_v, max_v = index_series.min(), index_series.max()
index_pct = (index_series - min_v)/(max_v - min_v)*100 if max_v!=min_v else pd.Series(50.0,index=index_series.index)

# ---------- Display GTI ----------
gti_today = float(index_pct.iloc[-1])
color_hex = gti_color(gti_today)
st.markdown(
    f"""
    <div style='display:flex; align-items:center; font-family:sans-serif;'>
        <!-- اللون -->
        <div style='width:28px; height:28px; border-radius:4px; background:{color_hex}; margin-right:10px;'></div>
        <!-- الرقم -->
        <span style='font-size:28px; font-weight:bold; color:{color_hex}; margin-right:10px;'>{gti_today:.2f}</span>
        <!-- النص -->
        <span style='font-size:20px; font-weight:500; color:#333;'>Today's GTI</span>
    </div>
    """,
    unsafe_allow_html=True
)

# Example: تجهيز البيانات
gti_df = pd.DataFrame({
    "Date": index_pct.index,
    "GTI": index_pct.values
})

# Selection عشان نتابع مكان الماوس على المحور X
hover = alt.selection_single(
    fields=["Date"],
    nearest=True,
    on="mousemove",
    empty="none",
    clear="mouseout"
)

# الخط الأساسي
line = alt.Chart(gti_df).mark_line(color="#4A90E2").encode(
    x=alt.X("Date:T", title="Date"),
    y=alt.Y("GTI:Q", title="GTI")
)

# نعمل rule عمودي يظهر مع حركة الماوس
rule = alt.Chart(gti_df).mark_rule(color="gray").encode(
    x="Date:T"
).add_selection(
    hover
).transform_filter(
    hover
)

# النص اللي هيظهر فوق الرسم
labels = alt.Chart(gti_df).mark_text(
    align="left", dx=5, dy=-5, color="black", fontSize=14, fontWeight="bold"
).encode(
    x="Date:T",
    y="GTI:Q",
    text=alt.condition(hover, "GTI:Q", alt.value(f"{gti_df.iloc[-1]['GTI']}"))
).transform_filter(
    hover
)

# لو خرجت من الرسم نرجع آخر قيمة (اليوم الحالي)
last_value = alt.Chart(pd.DataFrame([gti_df.iloc[-1]])).mark_text(
    align="left", dx=5, dy=-5, color="black", fontSize=14, fontWeight="bold"
).encode(
    x="Date:T",
    y="GTI:Q",
    text="GTI:Q"
).transform_filter(~hover)

# دمج الرسومات
chart = (line + rule + labels + last_value).properties(
    width=700,
    height=400
).interactive()

line = alt.Chart(gti_df).mark_line(color="#4A90E2").encode(
    x=alt.X("Date:T", title="Date"),
    y=alt.Y("GTI:Q", title="GTI")
)

tooltip = alt.Chart(gti_df).mark_rule(color="gray").encode(
    x="Date:T",
    y="GTI:Q",
    tooltip=[alt.Tooltip("Date:T", title="Date"), alt.Tooltip("GTI:Q", title="GTI")]
).add_selection(
    hover
).transform_filter(
    hover
)

chart = (line + tooltip).properties(
    width=700,
    height=400
).interactive()


st.altair_chart(chart, use_container_width=True)

# ---------- Table + Save/Restore ----------
st.markdown("### Adjust Weights Below")
col_table, col_buttons = st.columns([4,1])

editor_func = getattr(st, "data_editor", None) or getattr(st, "experimental_data_editor", None)

with col_table:
    if editor_func:
        edited = editor_func(weights, num_rows="dynamic", use_container_width=True, key="weights_editor")
    else:
        st.dataframe(weights, use_container_width=True)
        edited = weights.copy()

with col_buttons:
    if st.button("💾 Save Changes"):
        save_weights_local(edited, WEIGHTS_FILE)
        try:
            ok,msg = push_to_github(edited.to_csv(index=False), WEIGHTS_FILE, commit_message="Update weights via app")
            if ok: st.success("Saved locally and pushed to GitHub")
            else: st.warning(f"Saved locally. GitHub push skipped: {msg}")
        except Exception as e:
            st.warning(f"Saved locally. GitHub push failed: {e}")
        st.experimental_rerun()

    if st.button("♻️ Restore Original (from backup)"):
        if not os.path.exists(BACKUP_FILE):
            st.error(f"Backup file not found: {BACKUP_FILE}")
        else:
            shutil.copy(BACKUP_FILE, WEIGHTS_FILE)
            # optional push to GitHub
            try:
                with open(BACKUP_FILE,"r",encoding="utf-8") as f:
                    csv_text = f.read()
                if GITHUB_TOKEN and GITHUB_REPO:
                    ok,msg = push_to_github(csv_text, WEIGHTS_FILE, commit_message="Restore weights from backup")
                    if ok: st.success("Restored backup & pushed to GitHub")
                    else: st.warning(f"Restored locally. GitHub push failed: {msg}")
                else:
                    st.success("Restored locally from backup")
            except Exception as e:
                st.warning(f"Restored locally. GitHub push failed: {e}")
            st.experimental_rerun()
