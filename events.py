import requests
import streamlit as st
import pandas as pd

def show_events_table(start_date, end_date):
    try:
        # تحويل start & end للصيغة المطلوبة YYYYMMDDHHMMSS
        start = start_date.strftime("%Y%m%d%H%M%S")
        end = end_date.strftime("%Y%m%d%H%M%S")

        url = (
            f"https://api.gdeltproject.org/api/v2/events/summary"
            f"?QUERY=geopolitics"
            f"&STARTDATETIME={start}"
            f"&ENDDATETIME={end}"
            f"&MAXROWS=50"
            f"&FORMAT=json"
        )

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if "toparticles" not in data or not data["toparticles"]:
            st.info("No events found for the selected date range.")
            return

        # نحولها DataFrame
        df = pd.DataFrame(data["toparticles"])
        df = df[["url", "title", "seendate"]]

        # نعرضها بتنسيق حلو
        st.subheader("📰 Related News")
        for _, row in df.iterrows():
            st.markdown(f"- [{row['title']}]({row['url']}) ({row['seendate']})")

    except Exception as e:
        st.error(f"Error fetching events: {e}")
