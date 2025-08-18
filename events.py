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

        # HTML Table with alternating row colors and clickable links
        table_html = """
        <table style='width:100%; border-collapse: collapse; font-family: Arial, sans-serif;'>
            <thead>
                <tr style='background-color:#f2f2f2;'>
                    <th style='border-bottom: 2px solid #ddd; padding: 8px; text-align:left;'>Date</th>
                    <th style='border-bottom: 2px solid #ddd; padding: 8px; text-align:left;'>Title</th>
                    <th style='border-bottom: 2px solid #ddd; padding: 8px; text-align:left;'>Source</th>
                </tr>
            </thead>
            <tbody>
        """
        for i, (_, row) in enumerate(df.iterrows()):
            bg_color = "#ffffff" if i % 2 == 0 else "#f9f9f9"
            table_html += f"""
                <tr style='background-color:{bg_color};'>
                    <td style='border-bottom: 1px solid #ddd; padding: 6px;'>{row['Date']}</td>
                    <td style='border-bottom: 1px solid #ddd; padding: 6px;'>
                        <a href="{row['Link']}" target="_blank" style='text-decoration:none; color:#1a73e8;'>{row['Title']}</a>
                    </td>
                    <td style='border-bottom: 1px solid #ddd; padding: 6px;'>{row['Source']}</td>
                </tr>
            """
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error fetching events: {e}")
