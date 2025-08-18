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

def fetch_events(start_date, end_date, keywords=None):
    if keywords is None:
        keywords = DEFAULT_KEYWORDS
    
    all_events = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            # تاريخ النشر
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except:
                continue
            # ضمن الفترة المحددة؟
            if not (start_date <= pub_date.date() <= end_date):
                continue
            # النص يحتوي أي keyword؟
            if any(k.lower() in entry.title.lower() for k in keywords):
                all_events.append({
                    "Date": pub_date.date(),
                    "Title": entry.title,
                    "Source": entry.get("source", feed.feed.get("title","Unknown")),
                    "Link": entry.link
                })
    
    if not all_events:
        return pd.DataFrame(columns=["Date", "Title", "Source", "Link"])
    
    df = pd.DataFrame(all_events)
    df = df.sort_values("Date", ascending=False)
    return df

def show_events_table(start_date, end_date, keywords=None):
    try:
        df = fetch_events(start_date, end_date, keywords)
        if df.empty:
            st.info("No events found for the selected date range.")
            return

        st.markdown("### Important Events")

        # نستخدم st.write مع Markdown لكل صف
        for _, row in df.iterrows():
            date_str = row['Date'].strftime("%Y-%m-%d") if hasattr(row['Date'], 'strftime') else str(row['Date'])
            st.markdown(f"- **{date_str}** | [{row['Title']}]({row['Link']}) | {row['Source']}", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error fetching events: {e}")
