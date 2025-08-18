import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

def fetch_events(start_date=None, end_date=None):
    """
    يجلب الأحداث من GDELT API
    """

    if not start_date or not end_date:
        # لو المستخدم ما اختارش تواريخ، نجيب آخر أسبوع افتراضيًا
        end_date = datetime.today().strftime("%Y%m%d")
        start_date = (datetime.today() - timedelta(days=7)).strftime("%Y%m%d")
    else:
        start_date = pd.to_datetime(str(start_date), errors="coerce").strftime("%Y%m%d")
        end_date = pd.to_datetime(str(end_date), errors="coerce").strftime("%Y%m%d")

    url = (
        f"https://api.gdeltproject.org/api/v2/events/summary"
        f"?QUERY=geopolitics&STARTDATETIME={start_date}000000&ENDDATETIME={end_date}235959"
        f"&MAXROWS=50&FORMAT=json"
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # لو مافيش بيانات
        if "articles" not in data:
            return pd.DataFrame()

        events = data["articles"]

        # نحول الأحداث لـ DataFrame
        df = pd.DataFrame(events)

        if df.empty:
            return df

        # معالجة التاريخ بشكل آمن
        if "Date" in df.columns:
            df["Date"] = df["Date"].astype(str)  # نتأكد انه نص
            df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d", errors="coerce")
            df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

        # نتأكد إن في عنوان موجود
        if "Title" in df.columns:
            df = df.dropna(subset=["Title"])

        return df

    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame()


def show_events_table(start_date=None, end_date=None):
    """
    يعرض جدول الأحداث في Streamlit
    """
    df = fetch_events(start_date, end_date)

    if df.empty:
        st.info("No events found for the selected date range.")
    else:
        st.subheader("Geopolitical Events")
        st.dataframe(df[["Date", "Title", "SourceCommonName"]])
