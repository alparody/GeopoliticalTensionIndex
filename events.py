import requests
import pandas as pd
import streamlit as st

API_KEY = "pub_7302d3916fbb4ba7840008da0c481837"
BASE_URL = "https://newsdata.io/api/1/news"

def fetch_events(start_date: str, end_date: str):
    """يجلب أهم الأخبار الجيوسياسية بين تاريخين"""
    params = {
        "apikey": API_KEY,
        "q": "geopolitics",
        "language": "en",
        "from_date": start_date,  # لازم تكون YYYY-MM-DD
        "to_date": end_date,      # لازم تكون YYYY-MM-DD
        "country": "us,gb,eu",
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "results" not in data:
            return pd.DataFrame()

        events = [
            {"Date": item.get("pubDate", "")[:10], "Title": item.get("title", "")}
            for item in data["results"]
        ]
        return pd.DataFrame(events)

    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame()


def display_events(start_date: str, end_date: str):
    """يعرض جدول الأخبار بشكل منسق"""
    events_df = fetch_events(start_date, end_date)

    if events_df.empty:
        st.info("No events found for the selected date range.")
    else:
        st.subheader("📌 Key Geopolitical Events")
        st.dataframe(events_df, use_container_width=True)
