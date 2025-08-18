import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import base64
from github import Github
import io

# إعدادات الصفحة
st.set_page_config(page_title="Geopolitical Tension Index", layout="wide")

# ---- تحميل البيانات من GitHub ----
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "your-username/your-repo"   # ✨ غيره لاسم الريبو عندك
FILE_PATH = "weights.csv"

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)
file_content = repo.get_contents(FILE_PATH)
weights_df = pd.read_csv(io.StringIO(file_content.decoded_content.decode()))

# ---- حساب GTI ----
def calculate_gti(data):
    return (data["Weight"] * data["Value"]).sum() / data["Weight"].sum()

# بيانات تجريبية (ممكن تتغير بالـ API لاحقًا)
weights_df["Value"] = [30, 55, 70, 90]  # قيم مؤقتة للمصادر
gti_series = pd.Series(weights_df["Value"].rolling(2).mean())  # شكل مؤقت كخط زمني
gti_today = calculate_gti(weights_df)

# ---- لون المؤشر ----
def get_gti_color(value):
    if value < 40:
        return "green"
    elif value < 60:
        return "yellow"
    elif value < 80:
        return "orange"
    else:
        return "red"

# ---- عرض قيمة GTI ----
st.markdown(
    f"""
    <h2 style='text-align:center'>
    🛰️ Geopolitical Tension Index (GTI) اليوم: 
    <span style='color:{get_gti_color(gti_today)}'>{gti_today:.2f}</span>
    </h2>
    """,
    unsafe_allow_html=True
)

# ---- الرسم البياني ----
fig, ax = plt.subplots(figsize=(10,4))
ax.plot(gti_series.index, gti_series.values, label="GTI", color="blue")
ax.set_title("GTI Timeline")
ax.set_ylabel("GTI Value")
ax.legend()
st.pyplot(fig)

# ---- الجدول + الأزرار ----
st.subheader("جدول الأوزان")
edited_df = st.data_editor(weights_df, num_rows="dynamic", use_container_width=True)

col1, col2 = st.columns([1,1])

with col1:
    if st.button("💾 حفظ التعديلات"):
        csv_buffer = io.StringIO()
        edited_df.to_csv(csv_buffer, index=False)
        repo.update_file(FILE_PATH, "Update weights", csv_buffer.getvalue(), file_content.sha)
        st.success("تم حفظ التعديلات على GitHub ✅")

with col2:
    if st.button("🔄 استعادة القيم الأصلية"):
        repo.update_file(FILE_PATH, "Restore original weights", file_content.decoded_content.decode(), file_content.sha)
        st.warning("تم استعادة القيم الأصلية من GitHub ⚠️")

