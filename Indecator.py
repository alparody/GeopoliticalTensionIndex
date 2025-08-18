import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import shutil
import git
from datetime import datetime

# ملفات GitHub
CSV_FILE = "stocks_weights.csv"
BACKUP_FILE = "backup_weights.csv"
REPO_PATH = "./"  # غيره لو المشروع في مجلد تاني

# تحميل البيانات
def load_data():
    return pd.read_csv(CSV_FILE)

# حفظ البيانات + رفعها على GitHub
def save_data(df, message="Updated weights"):
    df.to_csv(CSV_FILE, index=False)

    try:
        repo = git.Repo(REPO_PATH)
        repo.git.add(CSV_FILE)
        repo.index.commit(message)
        origin = repo.remote(name="origin")
        origin.push()
    except Exception as e:
        st.error(f"GitHub push failed: {e}")

# استرجاع النسخة الأصلية
def restore_backup():
    if os.path.exists(BACKUP_FILE):
        shutil.copy(BACKUP_FILE, CSV_FILE)
        try:
            repo = git.Repo(REPO_PATH)
            repo.git.add(CSV_FILE)
            repo.index.commit("Restored from backup")
            origin = repo.remote(name="origin")
            origin.push()
        except Exception as e:
            st.error(f"GitHub push failed: {e}")
    else:
        st.error("Backup file not found!")

# حساب GTI
def calculate_gti(df):
    gti = (df["Value"] * df["Weight"]).sum() / 100
    return round(gti, 2)

# لون المربع حسب مستوى الخطورة
def risk_color(gti):
    if gti < 40:
        return "green"
    elif gti < 60:
        return "yellow"
    elif gti < 80:
        return "orange"
    else:
        return "red"

# واجهة Streamlit
st.title("Geopolitical Tension Index (GTI) Dashboard")

# تحميل البيانات
df = load_data()

# حساب GTI
gti_value = calculate_gti(df)

# عرض قيمة GTI ومربع اللون
st.markdown(
    f"""
    <div style="display:flex; align-items:center; font-size:24px; font-weight:bold;">
        Current GTI: {gti_value}
        <div style="width:25px; height:25px; background:{risk_color(gti_value)}; margin-left:15px; border-radius:5px;"></div>
    </div>
    """,
    unsafe_allow_html=True
)

# رسم GTI فقط
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot([datetime.today()], [gti_value], "o-", label="GTI", color="blue")
ax.set_ylabel("GTI Value")
ax.set_title("GTI Today")
ax.legend()
st.pyplot(fig)

# جدول التعديلات
st.subheader("Adjust Weights")
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

# أزرار التحكم
col1, col2 = st.columns(2)
with col1:
    if st.button("💾 Save Changes"):
        save_data(edited_df, "User updated weights")
        st.success("Changes saved and pushed to GitHub!")

with col2:
    if st.button("♻️ Restore Original"):
        restore_backup()
        st.success("Restored from backup!")
