import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
from streamlit_autorefresh import st_autorefresh

# ---------------- SAYFA AYARLARI ----------------
st.set_page_config(
    page_title="Toprak İzleme",
    page_icon="🌱",
    layout="wide"
)

# ---------------- ÖZEL CSS (Toprak & Bitki Teması) ----------------
st.markdown("""
<style>
    .stApp { background-color: #f5f0e8; }
    section[data-testid="stSidebar"] { background-color: #2d4a1e; }
    section[data-testid="stSidebar"] * { color: #d4e8b0 !important; }
    section[data-testid="stSidebar"] .stDateInput label,
    section[data-testid="stSidebar"] h2 { color: #a8d47a !important; font-weight: 700; }
    .stApp, .stApp p, .stApp span, .stApp div,
    .stApp label, .stApp li, .stApp td, .stApp th { color: #111111 !important; }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1.5px solid #7a9e4a;
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 2px 8px rgba(74, 90, 30, 0.10);
    }
    div[data-testid="metric-container"] label { color: #111111 !important; font-weight: 600; font-size: 1rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #111111 !important; font-size: 2rem !important; font-weight: 700; }
    h2, h3 { color: #111111 !important; border-left: 5px solid #7a9e4a; padding-left: 10px; }
    h1 { color: #111111 !important; }
    .stMarkdown, .stMarkdown p, .stMarkdown span { color: #111111 !important; }
    .stAlert p, .stAlert div, .stAlert span { color: #111111 !important; }
    .stDataFrame { border: 1px solid #a8c47a; border-radius: 10px; overflow: hidden; }
    .stDownloadButton > button, .stButton > button {
        background-color: #4a7c2a !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600;
        padding: 0.4rem 1.2rem;
        transition: background 0.2s;
    }
    .stDownloadButton > button:hover, .stButton > button:hover {
        background-color: #2d4a1e !important;
        color: #ffffff !important;
    }
    hr { border-color: #c5a96a !important; }
    .stTextInput > div > input {
        border: 1px solid #7a9e4a !important;
        border-radius: 8px !important;
        background-color: #faf7f0 !important;
        color: #111111 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Karşılama Başlığı ──
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
            Akıllı Toprak İzleme Paneli
        </h1>
        <p style="color: #a8c47a; margin: 4px 0 0; font-size: 0.95rem;">
            Smart Soil Monitoring Dashboard
        </p>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------- GİRİŞ ----------------
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
        <h2 style="color: #2d4a1e; border: none; padding: 0;">Giriş Yap</h2>
        <p style="color: #7a9e4a; font-size: 0.9rem;">Toprak İzleme Sistemi</p>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        user = st.text_input("👤 Kullanıcı Adı")
        pwd  = st.text_input("🔒 Şifre", type="password")
        if st.button("🌱 Giriş"):
            if (
                user == st.secrets["auth"]["username"] and
                pwd  == st.secrets["auth"]["password"]
            ):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ Kullanıcı adı veya şifre hatalı")

if not st.session_state.logged_in:
    login()
    st.stop()


# ---------------- ÇIKIŞ ----------------
col1, col2 = st.columns([8, 1])
with col2:
    if st.button("🚪 Çıkış"):
        st.session_state.logged_in = False
        st.rerun()


# ---------------- OTOMATİK YENİLEME ----------------
st_autorefresh(interval=10_000, key="soilrefresh")


# ---------------- FIREBASE BAŞLATMA ----------------
if not firebase_admin._apps:
    firebase_config = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(
        cred,
        {"databaseURL": firebase_config["databaseURL"]},
    )


# ---------------- VERİ YÜKLEME ----------------
@st.cache_data(ttl=5)
def load_data():
    ref = db.reference("basil_sorted")
    return ref.get()

data = load_data()

if not data:
    st.warning("⚠️ Sensörlerden gelen veri bulunamadı")
    st.stop()


# ---------------- DATAFRAME ----------------
records = []
for key, value in data.items():
    if isinstance(value, dict):
        records.append({
            "time":        key,
            "temperature": value.get("temperature"),
            "moisture":    value.get("moisture"),
        })

df = pd.DataFrame(records)

if df.empty:
    st.error("❌ Sensörlerden geçerli okuma bulunamadı")
    st.stop()

df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d_%H:%M:%S")
df = df.sort_values("time")


# ---------------- SON DEĞERLER ----------------
latest = df.iloc[-1]

moisture_val = latest["moisture"]
if moisture_val < 30:
    soil_status = "🏜️ Kuru — Sulama Gerekiyor"
    status_color = "#c0392b"
elif moisture_val < 60:
    soil_status = "✅ İdeal — Sağlıklı"
    status_color = "#27ae60"
else:
    soil_status = "💧 Doygun — Dikkat Et"
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
    <span style="font-size: 1rem; color: #111111; font-weight: 600;">Mevcut Toprak Durumu:</span>
    <span style="font-size: 1rem; font-weight: 700; color: {status_color};">{soil_status}</span>
    <span style="margin-left: auto; font-size: 0.8rem; color: #333333;">
        Son Güncelleme: {latest['time'].strftime('%Y-%m-%d %H:%M:%S')}
    </span>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
col1.metric("🌡️ Toprak Sıcaklığı",  f"{latest['temperature']} °C")
col2.metric("💧 Toprak Nemi",         f"{moisture_val} %")
col3.metric("📊 Toplam Okuma Sayısı", f"{len(df)} okuma")

st.divider()


# ---------------- KENAR ÇUBUĞU FİLTRESİ ----------------
st.sidebar.markdown("## 🌿 Veri Filtrele")
min_date = df["time"].min().date()
max_date = df["time"].max().date()

start = st.sidebar.date_input("📅 Başlangıç Tarihi", min_date)
end   = st.sidebar.date_input("📅 Bitiş Tarihi",     max_date)

df_filtered = df[
    (df["time"].dt.date >= start) &
    (df["time"].dt.date <= end)
]

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style="text-align:center; padding: 0.5rem;">
    <div style="font-size: 0.85rem; color: #a8d47a;">
        Filtrelenmiş Okuma Sayısı<br>
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
FONT_COLOR  = "#111111"

# CHART_LAYOUT بدون yaxis لتجنب التعارض مع fig3
BASE_LAYOUT = dict(
    paper_bgcolor = PAPER_BG,
    plot_bgcolor  = PAPER_BG,
    font          = dict(color=FONT_COLOR, family="Arial, sans-serif"),
    xaxis         = dict(gridcolor=GRID_COLOR, showgrid=True),
    yaxis         = dict(gridcolor=GRID_COLOR, showgrid=True),
    margin        = dict(l=40, r=20, t=50, b=40),
    hoverlabel    = dict(bgcolor="#2d4a1e", font_color="#d4e8b0"),
)

# Layout مخصص لـ fig3 (بدون yaxis الافتراضي لأنه يُعرَّف يدوياً)
DUAL_AXIS_LAYOUT = dict(
    paper_bgcolor = PAPER_BG,
    plot_bgcolor  = PAPER_BG,
    font          = dict(color=FONT_COLOR, family="Arial, sans-serif"),
    xaxis         = dict(gridcolor=GRID_COLOR, showgrid=True),
    margin        = dict(l=40, r=20, t=50, b=40),
    hoverlabel    = dict(bgcolor="#2d4a1e", font_color="#d4e8b0"),
)


# ---------------- SICAKLIK GRAFİĞİ ----------------
st.subheader("🌡️ Zaman İçinde Toprak Sıcaklığı")

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x    = df_filtered["time"],
    y    = df_filtered["temperature"],
    mode = "lines+markers",
    name = "Sıcaklık °C",
    line = dict(color=SOIL_BROWN, width=2.5),
    marker = dict(size=5, color=SOIL_BROWN, symbol="circle"),
    fill = "tozeroy",
    fillcolor = "rgba(139, 105, 20, 0.10)",
))
fig1.update_layout(
    title="🌡️ Sıcaklık Değişimi",
    **BASE_LAYOUT
)
fig1.update_yaxes(title_text="°C", title_font_color=SOIL_BROWN)
st.plotly_chart(fig1, use_container_width=True)


# ---------------- NEM GRAFİĞİ ----------------
st.subheader("💧 Zaman İçinde Toprak Nemi")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x    = df_filtered["time"],
    y    = df_filtered["moisture"],
    mode = "lines+markers",
    name = "Nem %",
    line = dict(color=PLANT_GREEN, width=2.5),
    marker = dict(size=5, color=PLANT_GREEN, symbol="circle"),
    fill = "tozeroy",
    fillcolor = "rgba(74, 124, 42, 0.10)",
))
fig2.add_hline(
    y=60, line_dash="dot",
    line_color="#c0392b", opacity=0.5,
    annotation_text="Üst İdeal Sınır",
    annotation_position="top right",
    annotation_font_color="#c0392b",
)
fig2.add_hline(
    y=30, line_dash="dot",
    line_color="#e67e22", opacity=0.5,
    annotation_text="Alt İdeal Sınır",
    annotation_position="bottom right",
    annotation_font_color="#e67e22",
)
fig2.update_layout(
    title="💧 Toprak Nemi Değişimi",
    **BASE_LAYOUT
)
fig2.update_yaxes(title_text="%", title_font_color=PLANT_GREEN)
st.plotly_chart(fig2, use_container_width=True)


# ---------------- BİRLEŞİK GRAFİK ----------------
st.subheader("📊 Sıcaklık ve Nem Karşılaştırması")

fig3 = go.Figure()
fig3.add_trace(go.Bar(
    x    = df_filtered["time"],
    y    = df_filtered["temperature"],
    name = "Sıcaklık °C",
    marker_color = SOIL_BROWN,
    opacity = 0.75,
    yaxis = "y1",
))
fig3.add_trace(go.Scatter(
    x    = df_filtered["time"],
    y    = df_filtered["moisture"],
    name = "Nem %",
    line = dict(color=PLANT_GREEN, width=2.5),
    mode = "lines",
    yaxis = "y2",
))
# ✅ الإصلاح: استخدام DUAL_AXIS_LAYOUT بدلاً من BASE_LAYOUT لتجنب تعارض yaxis
fig3.update_layout(
    **DUAL_AXIS_LAYOUT,
    yaxis=dict(
        title="Sıcaklık °C",
        title_font=dict(color=SOIL_BROWN),
        tickfont=dict(color=SOIL_BROWN),
        gridcolor=GRID_COLOR,
    ),
    yaxis2=dict(
        title="Nem %",
        overlaying="y",
        side="right",
        title_font=dict(color=PLANT_GREEN),
        tickfont=dict(color=PLANT_GREEN),
    ),
    legend=dict(orientation="h", y=1.1),
    barmode="overlay",
)
st.plotly_chart(fig3, use_container_width=True)


# ---------------- VERİ TABLOSU & CSV İNDİR ----------------
st.subheader("📋 Veri Tablosu")

display_df = df_filtered[["time", "temperature", "moisture"]].copy()
display_df["time"] = display_df["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
display_df = display_df.reset_index(drop=True)

rows_html = ""
for i, row in display_df.iterrows():
    bg = "#1e1e1e" if i % 2 == 0 else "#2a2a2a"
    rows_html += f"""
    <tr style="background:{bg};">
        <td style="padding:10px 14px; color:#cccccc; font-size:0.85rem;">{i}</td>
        <td style="padding:10px 14px; color:#ffffff; font-size:0.9rem;">{row['time']}</td>
        <td style="padding:10px 14px; color:#ffffff; font-size:0.9rem; text-align:right;">{row['temperature']}</td>
        <td style="padding:10px 14px; color:#ffffff; font-size:0.9rem; text-align:right;">{row['moisture']}</td>
    </tr>
    """

# ✅ الإصلاح: تصحيح اسم العمود من humidity إلى moisture
table_html = f"""
<div style="
    background: #111111;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #333333;
    margin-bottom: 1rem;
">
    <table style="width:100%; border-collapse:collapse;">
        <thead>
            <tr style="background:#1a1a1a; border-bottom: 1px solid #444;">
                <th style="padding:12px 14px; color:#aaaaaa; font-weight:600; text-align:left; font-size:0.85rem;"></th>
                <th style="padding:12px 14px; color:#aaaaaa; font-weight:600; text-align:left; font-size:0.85rem;">time</th>
                <th style="padding:12px 14px; color:#aaaaaa; font-weight:600; text-align:right; font-size:0.85rem;">temperature</th>
                <th style="padding:12px 14px; color:#aaaaaa; font-weight:600; text-align:right; font-size:0.85rem;">moisture</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
</div>
"""

st.markdown(table_html, unsafe_allow_html=True)

# CSV İndir
export_df = df_filtered.copy()
export_df["time"] = export_df["time"].dt.strftime("%Y-%m-%d %H:%M:%S")

csv = export_df[["time", "temperature", "moisture"]].to_csv(index=False, sep=";")

st.download_button(
    "⬇ Download CSV",
    csv,
    "soil_data.csv",
    "text/csv"
)

# ---------------- ALT BİLGİ ----------------
st.markdown("""
<div style="
    margin-top: 2rem;
    padding: 1rem;
    border-top: 1px solid #c5a96a;
    text-align: center;
    color: #111111;
    font-size: 0.85rem;
">
    🌱 Akıllı Toprak İzleme Sistemi &nbsp;|&nbsp; 
    🔄 Her 10 saniyede otomatik güncellenir &nbsp;|&nbsp;
    🌿 Smart Soil Monitor
</div>
""", unsafe_allow_html=True)
