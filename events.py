import requests
import pandas as pd
import streamlit as st

API_KEY = "pub_7302d3916fbb4ba7840008da0c481837"
BASE_URL = "https://newsdata.io/api/1/archive"


def fetch_events(start_date, end_date):
    """
    Fetch events from NewsData.io between start_date and end_date
    """
    try:
        url = f"{BASE_URL}?apikey={API_KEY}&q=geopolitics&language=en&from_date={start_date}&to_date={end_date}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if "results" not in data or len(data["results"]) == 0:
            return pd.DataFrame(columns=["Date", "Event Title", "Source", "Link"])

        events = []
        for article in data["results"]:
            events.append({
                "Date": article.get("pubDate", "")[:10],
                "Event Title": article.get("title", ""),
                "Source": article.get("source_id", ""),
                "Link": article.get("link", "")
            })

        return pd.DataFrame(events)

    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame(columns=["Date", "Event Title", "Source", "Link"])


def show_events_table(start_date, end_date):
    df = fetch_events(start_date, end_date)
    if df.empty:
        st.info("No events found for the selected period.")
    else:
        st.subheader("🌍 Major Geopolitical Events")
        # عرض الجدول مع روابط قابلة للضغط
        st.write(
            df.to_html(escape=False, index=False),
            unsafe_allow_html=True
        )
