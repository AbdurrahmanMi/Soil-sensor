import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Toprak İzleme Sistemi",
    page_icon="🌱",
    layout="wide"
)

# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=10000, key="refresh")

# ---------------- FIREBASE INIT ----------------
if not firebase_admin._apps:
    firebase_config = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(
        cred,
        {"databaseURL": firebase_config["databaseURL"]},
    )

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=5)
def load_data():
    ref = db.reference("dht_history")   # 🔴 تأكد من المسار الصحيح
    return ref.get()

data = load_data()

if not data:
    st.error("Veri yok ❌")
    st.stop()

# ---------------- PARSE DATA (FIXED) ----------------
records = []

for key, value in data.items():
    if isinstance(value, dict):
        records.append({
            "time": value.get("time", key),
            "temperature": value.get("temperature"),
            "moisture": value.get("moisture") or value.get("humidity")
        })

df = pd.DataFrame(records)

# تنظيف البيانات
df = df.dropna()
df["time"] = pd.to_datetime(df["time"])
df = df.sort_values("time").reset_index(drop=True)

if df.empty:
    st.error("Geçerli veri yok ❌")
    st.stop()

# ---------------- TITLE ----------------
st.title("🌱 Akıllı Toprak İzleme Paneli")

# ---------------- LATEST VALUES ----------------
latest = df.iloc[-1]

moisture = latest["moisture"]

if moisture < 30:
    soil_status = "🏜️ Kuru — Sulama gerekli"
    color = "red"
elif moisture < 60:
    soil_status = "✅ İdeal — Sağlıklı"
    color = "green"
else:
    soil_status = "💧 Çok nemli"
    color = "blue"

st.markdown(f"""
### Durum: <span style="color:{color}; font-weight:bold">{soil_status}</span>
""", unsafe_allow_html=True)

# ---------------- METRICS ----------------
col1, col2, col3 = st.columns(3)

col1.metric("🌡 Sıcaklık", f"{latest['temperature']} °C")
col2.metric("💧 Nem", f"{latest['moisture']} %")
col3.metric("📊 Kayıt", len(df))

# ---------------- FILTER ----------------
st.sidebar.header("Filtre")

start = st.sidebar.date_input("Başlangıç", df["time"].min().date())
end = st.sidebar.date_input("Bitiş", df["time"].max().date())

df = df[(df["time"].dt.date >= start) & (df["time"].dt.date <= end)]

# ---------------- CHART 1 ----------------
st.subheader("🌡 Sıcaklık Grafiği")

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=df["time"],
    y=df["temperature"],
    mode="lines+markers",
    line=dict(color="#8b6914")
))
st.plotly_chart(fig1, use_container_width=True)

# ---------------- CHART 2 ----------------
st.subheader("💧 Nem Grafiği")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=df["time"],
    y=df["moisture"],
    mode="lines+markers",
    line=dict(color="#4a7c2a")
))
st.plotly_chart(fig2, use_container_width=True)

# ---------------- TABLE ----------------
st.subheader("📋 Veri Tablosu")

show_df = df.copy()
show_df["time"] = show_df["time"].dt.strftime("%Y-%m-%d %H:%M:%S")

st.dataframe(show_df, use_container_width=True)
