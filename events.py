import requests
import streamlit as st
import pandas as pd


def fetch_events(start_date: str, end_date: str, query: str = "geopolitics"):
    """
    Fetch events/news from GDELT Doc API between start_date and end_date.
    Dates must be in format YYYYMMDDHHMMSS
    """
    try:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": 50,
            "format": "json",
            "startdatetime": start_date,
            "enddatetime": end_date,
        }

        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if "articles" not in data or len(data["articles"]) == 0:
            return pd.DataFrame()

        events = []
        for article in data["articles"]:
            events.append({
                "Date": article.get("seendate", "")[:8],  # YYYYMMDD
                "Source": article.get("sourceCommonName", ""),
                "Title": article.get("title", ""),
                "URL": article.get("url", ""),
            })

        return pd.DataFrame(events)

    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame()


def show_events_table(start_date: str, end_date: str):
    """
    Display events table in Streamlit sidebar
    Dates must be in format YYYYMMDDHHMMSS
    """
    st.sidebar.subheader("📅 Key Geopolitical Events")

    events_df = fetch_events(start_date, end_date)

    if events_df.empty:
        st.sidebar.info("No events found for the selected date range.")
    else:
        st.sidebar.dataframe(
            events_df[["Date", "Title", "Source"]],
            use_container_width=True,
            height=400,
        )
