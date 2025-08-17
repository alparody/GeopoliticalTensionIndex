import pandas as pd
import os

def load_stock_data():
    file_path = os.path.join(os.path.dirname(__file__), "data.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ملف البيانات مش موجود: {file_path}")
    df = pd.read_csv(file_path, parse_dates=["Date"])
    return df

def run_gti_test():
    df = load_stock_data()
    st.write("📊 البيانات المحملة:")
    st.dataframe(df)
