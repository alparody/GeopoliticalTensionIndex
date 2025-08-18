import requests
import pandas as pd
import streamlit as st

GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

def fetch_events(start_date, end_date):
    try:
        params = {
            "query": "geopolitics",
            "mode": "ArtList",
            "format": "json",
            "maxrecords": 20,
            "sort": "DateDesc",
            "startdatetime": start_date.replace("-", "") + "000000",
            "enddatetime": end_date.replace("-", "") + "235959",
        }
        response = requests.get(GDELT_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "articles" not in data:
            return pd.DataFrame()

        articles = data["articles"]
        df = pd.DataFrame([{
            "Date": a.get("seendate", "")[:8],
            "Title": a.get("title", ""),
            "Source": a.get("sourceurl", "")
        } for a in articles])

        # تحسين شكل الجدول
        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")

        return df
    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame()

def show_events_table(start_date, end_date):
    df = fetch_events(start_date, end_date)
    if df.empty:
        st.info("No events found for the selected date range.")
    else:
        st.subheader("📰 Key Geopolitical Events")
        st.dataframe(df, use_container_width=True, hide_index=True)
