import requests
import pandas as pd
import streamlit as st

API_KEY = "pub_7302d3916fbb4ba7840008da0c481837"

def fetch_events(start_date, end_date, query="geopolitics"):
    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": API_KEY,
        "q": query,
        "language": "en",
        "from_date": start_date,
        "to_date": end_date,
        "country": "us,gb,eu"  # تقدر تزود أو تقلل الدول
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if "results" not in data or not data["results"]:
            return pd.DataFrame(columns=["Date", "Event"])

        events = [
            {
                "Date": item.get("pubDate", "")[:10],
                "Event": item.get("title", "No Title")
            }
            for item in data["results"]
        ]
        return pd.DataFrame(events)

    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame(columns=["Date", "Event"])


def show_events_table(start_date, end_date):
    st.subheader("📌 Major Events")
    events_df = fetch_events(start_date, end_date)
    if events_df.empty:
        st.info("No major events found in this date range.")
    else:
        st.dataframe(events_df, use_container_width=True)
