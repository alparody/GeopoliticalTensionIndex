# index_analysis.py
import os
import json
from datetime import timedelta
import pandas as pd
import yfinance as yf
import plotly.express as px

# ---------- Config ----------
MARKETS_FILE = "markets_universe.json"

FALLBACK_MARKETS = [
  {"Country": "USA", "MainIndexName": "S&P 500", "YahooTicker": "^GSPC"},
  {"Country": "Germany", "MainIndexName": "DAX Performance Index", "YahooTicker": "^GDAXI"},
  {"Country": "UK", "MainIndexName": "FTSE 100", "YahooTicker": "^FTSE"},
  {"Country": "France", "MainIndexName": "CAC 40", "YahooTicker": "^FCHI"},
  {"Country": "Japan", "MainIndexName": "Nikkei 225", "YahooTicker": "^N225"},
  {"Country": "China", "MainIndexName": "SSE Composite Index", "YahooTicker": "000001.SS"},
  {"Country": "Hong Kong", "MainIndexName": "Hang Seng Index", "YahooTicker": "^HSI"},
  {"Country": "India", "MainIndexName": "Nifty 50", "YahooTicker": "^NSEI"},
  {"Country": "Saudi Arabia", "MainIndexName": "Tadawul All Share Index (TASI)", "YahooTicker": "^TASI.SR"},
  {"Country": "Egypt", "MainIndexName": "Commercial International Bank (CIB)", "YahooTicker": "COMI.CA"},
  {"Country": "Singapore", "MainIndexName": "Straits Times Index (STI)", "YahooTicker": "^STI"},
  {"Country": "South Korea", "MainIndexName": "Kospi", "YahooTicker": "^KS11"},
  {"Country": "Taiwan", "MainIndexName": "TAIEX", "YahooTicker": "^TWII"},
  {"Country": "Thailand", "MainIndexName": "SET Index", "YahooTicker": "^SET.BK"},
  {"Country": "Vietnam", "MainIndexName": "VN-Index", "YahooTicker": "^VNINDEX.VN"},
  {"Country": "Indonesia", "MainIndexName": "IDX Composite", "YahooTicker": "^JKSE"},
  {"Country": "Philippines", "MainIndexName": "PSEi", "YahooTicker": "PSEI.PS"},
  {"Country": "Malaysia", "MainIndexName": "FTSE KLCI", "YahooTicker": "^KLSE"},
  {"Country": "Israel", "MainIndexName": "TA-125", "YahooTicker": "TASE.TA"},
  {"Country": "Pakistan", "MainIndexName": "KSE-100", "YahooTicker": "PAK"}
]

ISO3_MAP = {
    "USA": "USA", "Germany": "DEU", "UK": "GBR", "France": "FRA", "Japan": "JPN",
    "China": "CHN", "Hong Kong": "HKG", "India": "IND", "Saudi Arabia": "SAU",
    "Egypt": "EGY", "Singapore": "SGP", "South Korea": "KOR", "Taiwan": "TWN",
    "Thailand": "THA", "Vietnam": "VNM", "Indonesia": "IDN", "Philippines": "PHL",
    "Malaysia": "MYS", "Israel": "ISR", "Pakistan": "PAK"
}

# ---------- Helpers ----------
def load_markets(path: str = MARKETS_FILE) -> pd.DataFrame:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = FALLBACK_MARKETS
    df = pd.DataFrame(data)
    required = {"Country", "YahooTicker"}
    if not required.issubset(df.columns):
        raise ValueError("Markets JSON must include at least: Country, YahooTicker")
    df["MainIndexName"] = df.get("MainIndexName", df["YahooTicker"])
    df["ISO3"] = df["Country"].map(ISO3_MAP)
    return df

def _download_close(ticker: str, start, end) -> pd.Series:
    try:
        df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if df is None or df.empty or "Close" not in df:
            return pd.Series(dtype="float64")
        return df["Close"].dropna()
    except Exception:
        return pd.Series(dtype="float64")

def _closest_prior(index: pd.DatetimeIndex, target) -> pd.Timestamp | None:
    ts = pd.to_datetime(target)
    pos = index.searchsorted(ts, side="right") - 1
    if pos < 0:
        return None
    return index[pos]

def _pct_change_over(series: pd.Series, days: int, asof) -> float | None:
    if series.empty:
        return None
    end_idx = _closest_prior(series.index, asof)
    if end_idx is None:
        return None
    start_target = pd.to_datetime(asof) - timedelta(days=days)
    start_idx = _closest_prior(series.index, start_target)
    if start_idx is None:
        return None
    start_px = float(series.loc[start_idx])
    end_px = float(series.loc[end_idx])
    if start_px == 0:
        return None
    return (end_px - start_px) / start_px * 100.0

def _pct_change_daily(series: pd.Series, asof) -> float | None:
    if series.empty:
        return None
    end_idx = _closest_prior(series.index, asof)
    if end_idx is None:
        return None
    loc = series.index.get_loc(end_idx)
    if isinstance(loc, slice):
        loc = series.index.slice_indexer(end_idx, end_idx).stop - 1
    prev_pos = loc - 1
    if prev_pos < 0:
        return None
    prev_px = float(series.iloc[prev_pos])
    last_px = float(series.iloc[loc])
    if prev_px == 0:
        return None
    return (last_px - prev_px) / prev_px * 100.0

# ---------- Public API ----------
def build_results(start_date, end_date, today=None, markets_path: str = MARKETS_FILE) -> pd.DataFrame:
    if today is None:
        today = end_date

    markets = load_markets(markets_path)
    dl_start = pd.to_datetime(start_date) - timedelta(days=400)
    dl_end   = pd.to_datetime(end_date) + timedelta(days=1)

    rows = []
    for _, m in markets.iterrows():
        country, ticker, name, iso3 = m["Country"], m["YahooTicker"], m.get("MainIndexName", ""), m.get("ISO3")
        s = _download_close(ticker, dl_start, dl_end)
        status = "✅ OK" if not s.empty else "❌ Not Found"
        if s.empty:
            row = dict(Country=country, ISO3=iso3, MainIndexName=name, YahooTicker=ticker,
                       status=status, daily=None, weekly=None, monthly=None, yearly=None)
        else:
            d   = _pct_change_daily(s, today)
            w   = _pct_change_over(s, 7,   today)
            mon = _pct_change_over(s, 30,  today)
            yr  = _pct_change_over(s, 365, today)
            row = dict(Country=country, ISO3=iso3, MainIndexName=name, YahooTicker=ticker,
                       status=status, daily=d, weekly=w, monthly=mon, yearly=yr)
        rows.append(row)

    df = pd.DataFrame(rows)
    for col in ["daily", "weekly", "monthly", "yearly"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

# ---------- Color Classification ----------
def classify_color_class(row: pd.Series) -> str:
    y, m, w, d = row.get("yearly"), row.get("monthly"), row.get("weekly"), row.get("daily")

    def neg(x):
        return pd.notna(x) and x < 0

    if neg(y) and neg(m) and neg(w) and neg(d):
        return "RED"
    elif neg(m) and neg(w) and neg(d):
        return "ORANGE"
    elif neg(w) and neg(d):
        return "YELLOW"
    elif neg(d):
        return "LIGHT_GREEN"
    else:
        return "GREEN"

def attach_color_classes(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(ColorClass=df.apply(classify_color_class, axis=1))

# ---------- Plot World Map ----------
def plot_world_map(start_date, end_date, today=None, markets_path: str = MARKETS_FILE):
    df = build_results(start_date, end_date, today, markets_path)
    df = attach_color_classes(df)
    fig = px.choropleth(
        df,
        locations="ISO3",
        color="ColorClass",
        hover_name="Country",
        title=f"Global Markets Performance ({start_date} to {end_date})",
        color_discrete_map={
            "NEG_YEAR": "red",
            "NEG_MONTH_NO_YEAR": "orange",
            "NEG_WEEK_NO_MONTH": "yellow",
            "NEG_DAY_NO_WEEK": "lightgreen",
            "ALL_POSITIVE": "green"
        }
    )
    return fig
