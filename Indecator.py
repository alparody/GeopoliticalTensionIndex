import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")
st.title("Geopolitical Tension Index (% based on Colab logic)")

TICKERS = [
    'GC=F','CL=F',          # Commodities
    'LMT','NOC','RTX',      # US Defense
    'XOM','CVX','BP',       # US Energy
    'ZIM','AMKBY','CMRE',   # Shipping
    '2222.SR','2010.SR',    # Aramco, SABIC
    'QNBK.QA','QEWS.QA',    # Qatar
    'EGS740C1C010.CA',      # Suez Canal Tech Settling
    'COMI.CA'               # Commercial Intl Bank Egypt
]

col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.sidebar.date_input("From:", datetime.date.today() - datetime.timedelta(days=365))
with col2:
    end_date = st.sidebar.date_input("To:", datetime.date.today())

st.sidebar.header("Weights (%)")
weights = {t: st.sidebar.number_input(f"{t}", 0.0, 100.0, 10.0, 0.1) for t in TICKERS}

df = yf.download(TICKERS, start=start_date, end=end_date, interval="1d")['Close']
df = df.dropna(how='all', axis=1)

returns = df.pct_change().dropna()
weighted = pd.DataFrame({t: returns[t] * (weights.get(t,0)/100) for t in returns.columns})
index_pct = weighted.sum(axis=1).cumsum() * 100  # cumulative sum in pct

st.subheader("Tension Index (Cumulative %)")
st.line_chart(index_pct)

st.subheader("Latest Values")
st.table(index_pct.tail(10).rename("Index Value (%)").round(2).to_frame())

st.caption("Based on return × weight, cumulative — exact Colab logic")
