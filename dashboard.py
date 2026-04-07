import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="مراقبة التربة",
    page_icon="🌱",
    layout="wide"
)

# ---------------- CUSTOM CSS (Soil & Plant Theme) ----------------
st.markdown("""
<style>
    /* ── الخلفية العامة ── */
    .stApp {
        background-color: #f5f0e8;
    }

    /* ── الشريط الجانبي ── */
    section[data-testid="stSidebar"] {
        background-color: #2d4a1e;
    }
    section[data-testid="stSidebar"] * {
        color: #d4e8b0 !important;
    }
    section[data-testid="stSidebar"] .stDateInput label,
    section[data-testid="stSidebar"] h2 {
        color: #a8d47a !important;
        font-weight: 700;
    }

    /* ── بطاقات المقاييس ── */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1.5px solid #7a9e4a;
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 2px 8px rgba(74, 90, 30, 0.10);
    }
    div[data-testid="metric-container"] label {
        color: #5c7a2a !important;
        font-weight: 600;
        font-size: 1rem;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #2d4a1e !important;
        font-size: 2rem !important;
        font-weight: 700;
    }

    /* ── العناوين الفرعية ── */
    h2, h3 {
        color: #3b5e1e !important;
        border-left: 5px solid #7a9e4a;
        padding-left: 10px;
    }

    /* ── العنوان الرئيسي ── */
    h1 {
        color: #2d4a1e !important;
    }

    /* ── الجدول ── */
    .stDataFrame {
        border: 1px solid #a8c47a;
        border-radius: 10px;
        overflow: hidden;
    }

    /* ── زر التحميل والـ Logout ── */
    .stDownloadButton > button,
    .stButton > button {
        background-color: #4a7c2a !important;
        color: #f5f0e8 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600;
        padding: 0.4rem 1.2rem;
        transition: background 0.2s;
    }
    .stDownloadButton > button:hover,
    .stButton > button:hover {
        background-color: #2d4a1e !important;
    }

    /* ── فاصل ── */
    hr {
        border-color: #c5a96a !important;
    }

    /* ── حقول الإدخال عند تسجيل الدخول ── */
    .stTextInput > div > input {
        border: 1px solid #7a9e4a !important;
        border-radius: 8px !important;
        background-color: #faf7f0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── بانر ترحيبي ──
st.markdown("""
<div style="
    background: linear-gradient(135deg, #2d4a1e 0%, #4a7c2a 60%, #8b6914 100%);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 16px;
">
    <div style="font-size: 3rem;">🌱</div>
    <div>
        <h1 style="color: #d4e8b0 !important; margin: 0; font-size: 1.8rem;">
            لوحة مراقبة التربة الذكية
        </h1>
        <p style="color: #a8c47a; margin: 4px 0 0; font-size: 0.95rem;">
            Smart Soil Monitoring Dashboard
        </p>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------- LOGIN ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.markdown("""
    <div style="
        max-width: 420px; margin: 4rem auto;
        background: #fff;
        border: 1.5px solid #7a9e4a;
        border-radius: 16px;
        padding: 2.5rem;
        text-align: center;
    ">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">🌿</div>
        <h2 style="color: #2d4a1e; border: none; padding: 0;">تسجيل الدخول</h2>
        <p style="color: #7a9e4a; font-size: 0.9rem;">نظام مراقبة التربة</p>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        user = st.text_input("👤 اسم المستخدم")
        pwd  = st.text_input("🔒 كلمة المرور", type="password")
        if st.button("🌱 دخول"):
            if (
                user == st.secrets["auth"]["username"] and
                pwd  == st.secrets["auth"]["password"]
            ):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ بيانات الدخول غير صحيحة")

if not st.session_state.logged_in:
    login()
    st.stop()


# ---------------- LOGOUT ----------------
col1, col2 = st.columns([8, 1])
with col2:
    if st.button("🚪 خروج"):
        st.session_state.logged_in = False
        st.rerun()


# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=10_000, key="soilrefresh")


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
    ref = db.reference("dht_history")
    return ref.get()

data = load_data()

if not data:
    st.warning("⚠️ لا توجد بيانات متاحة من الحساسات")
    st.stop()


# ---------------- DATAFRAME ----------------
records = []
for key, value in data.items():
    if isinstance(value, dict):
        records.append({
            "time":        key,
            "temperature": value.get("temperature"),
            "humidity":    value.get("humidity"),
        })

df = pd.DataFrame(records)

if df.empty:
    st.error("❌ لا توجد قراءات صالحة من الحساسات")
    st.stop()

df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d_%H:%M:%S")
df = df.sort_values("time")


# ---------------- LATEST VALUES ----------------
latest = df.iloc[-1]

# تصنيف حالة التربة بناءً على الرطوبة
humidity_val = latest["humidity"]
if humidity_val < 30:
    soil_status = "🏜️ جافة — تحتاج ري"
    status_color = "#c0392b"
elif humidity_val < 60:
    soil_status = "✅ مثالية — صحية"
    status_color = "#27ae60"
else:
    soil_status = "💧 مشبعة — انتبه"
    status_color = "#2980b9"

st.markdown(f"""
<div style="
    background: #fff;
    border: 1.5px solid #7a9e4a;
    border-radius: 14px;
    padding: 1rem 1.5rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 12px;
">
    <span style="font-size: 1rem; color: #5c7a2a; font-weight: 600;">حالة التربة الحالية:</span>
    <span style="font-size: 1rem; font-weight: 700; color: {status_color};">{soil_status}</span>
    <span style="margin-right: auto; font-size: 0.8rem; color: #8b9e7a;">
        آخر تحديث: {latest['time'].strftime('%Y-%m-%d %H:%M:%S')}
    </span>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
col1.metric("🌡️ درجة حرارة التربة",  f"{latest['temperature']} °C")
col2.metric("💧 رطوبة التربة",         f"{humidity_val} %")
col3.metric("📊 إجمالي القراءات",      f"{len(df)} قراءة")

st.divider()


# ---------------- SIDEBAR FILTER ----------------
st.sidebar.markdown("## 🌿 تصفية البيانات")
min_date = df["time"].min().date()
max_date = df["time"].max().date()

start = st.sidebar.date_input("📅 من تاريخ", min_date)
end   = st.sidebar.date_input("📅 إلى تاريخ", max_date)

df_filtered = df[
    (df["time"].dt.date >= start) &
    (df["time"].dt.date <= end)
]

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style="text-align:center; padding: 0.5rem;">
    <div style="font-size: 0.85rem; color: #a8d47a;">
        عدد القراءات المُصفّاة<br>
        <span style="font-size: 1.4rem; font-weight: 700; color: #d4e8b0;">
            {len(df_filtered)}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)


# ── ألوان الرسوم البيانية ──
SOIL_BROWN  = "#8b6914"
PLANT_GREEN = "#4a7c2a"
PAPER_BG    = "#faf7f0"
GRID_COLOR  = "#ddd5c0"
FONT_COLOR  = "#2d4a1e"

CHART_LAYOUT = dict(
    paper_bgcolor = PAPER_BG,
    plot_bgcolor  = PAPER_BG,
    font          = dict(color=FONT_COLOR, family="Tajawal, Arial"),
    xaxis         = dict(gridcolor=GRID_COLOR, showgrid=True),
    yaxis         = dict(gridcolor=GRID_COLOR, showgrid=True),
    margin        = dict(l=40, r=20, t=50, b=40),
    hoverlabel    = dict(bgcolor="#2d4a1e", font_color="#d4e8b0"),
)


# ---------------- TEMPERATURE CHART ----------------
st.subheader("🌡️ درجة حرارة التربة عبر الزمن")

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x    = df_filtered["time"],
    y    = df_filtered["temperature"],
    mode = "lines+markers",
    name = "الحرارة °C",
    line = dict(color=SOIL_BROWN, width=2.5),
    marker = dict(size=5, color=SOIL_BROWN, symbol="circle"),
    fill = "tozeroy",
    fillcolor = "rgba(139, 105, 20, 0.10)",
))
fig1.update_layout(
    title = "🌡️ تغيّر درجة الحرارة",
    **CHART_LAYOUT
)
fig1.update_yaxes(title_text="°C", title_font_color=SOIL_BROWN)
st.plotly_chart(fig1, use_container_width=True)


# ---------------- HUMIDITY CHART ----------------
st.subheader("💧 رطوبة التربة عبر الزمن")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x    = df_filtered["time"],
    y    = df_filtered["humidity"],
    mode = "lines+markers",
    name = "الرطوبة %",
    line = dict(color=PLANT_GREEN, width=2.5),
    marker = dict(size=5, color=PLANT_GREEN, symbol="circle"),
    fill = "tozeroy",
    fillcolor = "rgba(74, 124, 42, 0.10)",
))

# خط مرجعي للمستوى المثالي
fig2.add_hline(
    y=60, line_dash="dot",
    line_color="#c0392b", opacity=0.5,
    annotation_text="الحد الأعلى المثالي",
    annotation_position="top right",
    annotation_font_color="#c0392b",
)
fig2.add_hline(
    y=30, line_dash="dot",
    line_color="#e67e22", opacity=0.5,
    annotation_text="الحد الأدنى المثالي",
    annotation_position="bottom right",
    annotation_font_color="#e67e22",
)
fig2.update_layout(
    title = "💧 تغيّر رطوبة التربة",
    **CHART_LAYOUT
)
fig2.update_yaxes(title_text="%", title_font_color=PLANT_GREEN)
st.plotly_chart(fig2, use_container_width=True)


# ---------------- COMBINED CHART ----------------
st.subheader("📊 مقارنة الحرارة والرطوبة")

fig3 = go.Figure()
fig3.add_trace(go.Bar(
    x    = df_filtered["time"],
    y    = df_filtered["temperature"],
    name = "الحرارة °C",
    marker_color = SOIL_BROWN,
    opacity = 0.75,
    yaxis = "y1",
))
fig3.add_trace(go.Scatter(
    x    = df_filtered["time"],
    y    = df_filtered["humidity"],
    name = "الرطوبة %",
    line = dict(color=PLANT_GREEN, width=2.5),
    mode = "lines",
    yaxis = "y2",
))
fig3.update_layout(
    yaxis  = dict(title="درجة الحرارة °C", titlefont_color=SOIL_BROWN,
                  tickfont_color=SOIL_BROWN, gridcolor=GRID_COLOR),
    yaxis2 = dict(title="الرطوبة %", overlaying="y", side="right",
                  titlefont_color=PLANT_GREEN, tickfont_color=PLANT_GREEN),
    legend = dict(orientation="h", y=1.1),
    barmode = "overlay",
    **CHART_LAYOUT
)
st.plotly_chart(fig3, use_container_width=True)


# ---------------- DATA TABLE ----------------
st.subheader("📋 جدول القراءات التفصيلية")

display_df = df_filtered[["time", "temperature", "humidity"]].copy()
display_df.columns = ["🕒 الوقت", "🌡️ الحرارة (°C)", "💧 الرطوبة (%)"]
display_df["🕒 الوقت"] = display_df["🕒 الوقت"].dt.strftime("%Y-%m-%d %H:%M:%S")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)


# ---------------- CSV EXPORT ----------------
export_df = df_filtered.copy()
export_df["time"] = export_df["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
csv = export_df[["time", "temperature", "humidity"]].to_csv(
    index=False, sep=";"
)

col_a, col_b = st.columns([3, 1])
with col_b:
    st.download_button(
        label    = "⬇️ تحميل البيانات CSV",
        data     = csv,
        file_name= "soil_data.csv",
        mime     = "text/csv",
    )


# ---------------- FOOTER ----------------
st.markdown("""
<div style="
    margin-top: 2rem;
    padding: 1rem;
    border-top: 1px solid #c5a96a;
    text-align: center;
    color: #7a9e4a;
    font-size: 0.85rem;
">
    🌱 نظام مراقبة التربة الذكي &nbsp;|&nbsp; 
    🔄 يتجدد تلقائياً كل 10 ثوان &nbsp;|&nbsp;
    🌿 Smart Soil Monitor
</div>
""", unsafe_allow_html=True)