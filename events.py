# events.py
import streamlit as st
import pandas as pd
import feedparser
from datetime import datetime

# --------- RSS Sources ---------
RSS_FEEDS = [
    "https://www.aljazeera.com/xml/rss/all.xml",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "http://feeds.reuters.com/reuters/topNews"
]

# --------- Default Keywords ---------
DEFAULT_KEYWORDS = ["geopolitics", "economic", "war", "conflict", "trade", "sanctions"]

def fetch_events(start_date, end_date):
    try:
        feed = feedparser.parse(RSS_FEED_URL)
        items = []
        for entry in feed.entries:
            # تحويل التاريخ من feed
            pub_date = datetime(*entry.published_parsed[:6])
            if start_date <= pub_date.date() <= end_date:
                # فلترة حسب الكلمات المفتاحية في العنوان أو الوصف
                text = (entry.title + " " + getattr(entry, "summary", "")).lower()
                if any(k.lower() in text for k in KEYWORDS):
                    items.append({
                        "Date": pub_date.strftime("%Y-%m-%d"),
                        "Title": entry.title,
                        "Link": entry.link
                    })
        if not items:
            return pd.DataFrame(columns=["Date", "Title", "Link"])
        df = pd.DataFrame(items)
        return df.sort_values(by="Date", ascending=False)
    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame(columns=["Date", "Title", "Link"])

def show_events_table(start_date, end_date):
    df = fetch_events(start_date, end_date)
    if df.empty:
        st.info("No events found for the selected date range.")
        return
    # تحويل العنوان إلى HTML clickable link
    df["Title"] = df.apply(lambda x: f'<a href="{x["Link"]}" target="_blank">{x["Title"]}</a>', axis=1)
    # عرض الجدول في Streamlit
    st.markdown(
        df[["Date", "Title"]].to_html(escape=False, index=False),
        unsafe_allow_html=True
    )
