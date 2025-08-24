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

# --------- تصنيفات المخاطر حسب الكلمات المفتاحية ---------
RISK_KEYWORDS = {
    "High": ["war", "conflict", "attack", "violence", "invasion"],
    "Medium": ["sanctions", "tension", "dispute", "protest"],
    "Low": ["trade", "economic", "policy", "agreement"]
}

RISK_ORDER = {"High": 1, "Medium": 2, "Low": 3}

def classify_risk(title: str) -> str:
    """تحديد مستوى الخطورة من عنوان الخبر"""
    title_lower = title.lower()
    for risk, keywords in RISK_KEYWORDS.items():
        if any(k in title_lower for k in keywords):
            return risk
    return "Low"

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
                risk_level = classify_risk(entry.title)
                all_events.append({
                    "Date": pub_date.date(),
                    "Title": entry.title,
                    "Source": entry.get("source", feed.feed.get("title","Unknown")),
                    "Link": entry.link,
                    "Risk": risk_level
                })
    
    if not all_events:
        return pd.DataFrame(columns=["Date", "Title", "Source", "Link", "Risk"])
    
    df = pd.DataFrame(all_events)
    # ترتيب: أولًا الخطورة، ثم التاريخ تنازلي
    df["RiskOrder"] = df["Risk"].map(RISK_ORDER)
    df = df.sort_values(by=["RiskOrder", "Date"], ascending=[True, False])
    return df

def show_events_table(start_date, end_date, keywords=None):
    try:
        df = fetch_events(start_date, end_date, keywords)
        if df.empty:
            st.info("No events found for the selected date range.")
            return

        st.markdown("### Important Events (Sorted by Risk)")

        for _, row in df.iterrows():
            date_str = row['Date'].strftime("%Y-%m-%d") if hasattr(row['Date'], 'strftime') else str(row['Date'])
            
            risk_color = {
                "High": "🔴 High",
                "Medium": "🟠 Medium",
                "Low": "🟡 Low"
            }.get(row['Risk'], "🟡 Low")

            st.markdown(
                f"**{risk_color}** | {date_str} | [{row['Title']}]({row['Link']})",
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Error fetching events: {e}")
