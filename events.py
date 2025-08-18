import requests
import pandas as pd
import streamlit as st

API_KEY = "pub_7302d3916fbb4ba7840008da0c481837"
BASE_URL = "https://newsapi.org/v2/everything"

def fetch_events(start_date, end_date):
    """
    Fetch events between start_date and end_date
    """
    try:
        url = f"{BASE_URL}?q=geopolitics&from={start_date}&to={end_date}&language=en&sortBy=popularity&apiKey={API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if "articles" not in data or len(data["articles"]) == 0:
            return pd.DataFrame(columns=["Date", "Event Title", "Source"])

        events = []
        for article in data["articles"]:
            events.append({
                "Date": article["publishedAt"][:10],
                "Event Title": article["title"],
                "Source": article["source"]["name"]
            })

        return pd.DataFrame(events)

    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame(columns=["Date", "Event Title", "Source"])


def show_events_table(start_date, end_date):
    df = fetch_events(start_date, end_date)
    if df.empty:
        st.info("No events found for the selected period.")
    else:
        st.subheader("🌍 Major Geopolitical Events")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
