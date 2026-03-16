import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from PIL import Image, ImageDraw
import requests
from io import BytesIO
from streamlit_image_coordinates import streamlit_image_coordinates

# --- 1. DATA KONEKSI (Sesuai Dashboard Bapak) ---
USER = "3oNapQCmXkUdxGF.root"
HOST = "gateway01.southeast-1.prod.aws.tidbcloud.com"
PORT = 4000
DB_NAME = "test"
# PASTIKAN BAPAK SUDAH KLIK 'GENERATE PASSWORD' DAN MASUKKAN DI SINI
PASS = "ZsUvxG2dfGphBedY" 

@st.cache_resource
def init_db():
    engine = create_engine(
        f"mysql+mysqlconnector://{USER}:{PASS}@{HOST}:{PORT}/{DB_NAME}",
        connect_args={"ssl_disabled": False},
        pool_pre_ping=True
    )
    
    # Otomatis buat tabel jika belum ada
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS master_lokasi (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lokasi VARCHAR(50) UNIQUE,
                lantai VARCHAR(50),
                url_gambar TEXT,
                x_coord INT DEFAULT 0,
                y_coord INT DEFAULT 0
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stok_toko (
                id INT AUTO_INCREMENT PRIMARY KEY,
                Nama_Barang TEXT,
                Brand VARCHAR(100),
                Kode_Lokasi VARCHAR(50),
                Qty_St_ok INT
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS peta_lantai (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nama_lantai VARCHAR(50) UNIQUE,
                url_peta TEXT
            );
        """))
    return engine

engine = init_db()

# --- 2. FUNGSI GAMBAR ---
def get_image(file_id):
    if not file_id or len(str(file_id)) < 5: return None
    clean_id = str(file_id).split('id=')[-1].split('/')[-1].split('?')[0]
    url = f"https://drive.google.com/uc?export=download&id={clean_id}"
    try:
        res = requests.get(url, timeout=10)
        return Image.open(BytesIO(res.content)) if res.status_code == 200 else None
    except: return None

# --- 3. UI UTAMA ---
st.set_page_config(page_title="GMB Integrated Online", layout="wide")

with st.sidebar:
    st.title("🏗️ GMB System")
    st.success("Connected to TiDB Cloud")
    fitur = st.radio("Menu:", ["Peta Navigasi", "Dashboard & Stok", "Kalibrasi", "Upload Center"])

# MODUL: PETA NAVIGASI
if fitur == "Peta Navigasi":
    st.subheader("📍 Navigasi Gudang Online")
    try:
        query = text("SELECT s.Nama_Barang, s.Kode_Lokasi, l.lantai, l.x_coord, l.y_coord, l.url_gambar FROM stok_toko s JOIN master_lokasi l ON s.Kode_Lokasi = l.lokasi")
        df = pd.read_sql(query, con=engine)
        if df.empty:
            st.warning("Data stok masih kosong. Silakan isi di menu Upload Center.")
        else:
            pilih = st.selectbox("Cari Barang:", sorted(df['Nama_Barang'].unique()))
            t = df[df['Nama_Barang'] == pilih].iloc[0]
            
            c1, c2 = st.columns([2, 1])
            with c1:
                q_p = text("SELECT url_peta FROM peta_lantai WHERE nama_lantai = :lt")
                with engine.connect() as conn:
                    p_res = conn.execute(q_p, {"lt": t['lantai']}).fetchone()
                if p_res:
                    img = get_image(p_res[0])
                    if img:
                        draw = ImageDraw.Draw(img)
                        draw.ellipse((t['x_coord']-25, t['y_coord']-25, t['x_coord']+25, t['y_coord']+25), fill="red", outline="white", width=5)
                        st.image(img, use_container_width=True)
            with c2:
                img_r = get_image(t['url_gambar'])
                if img_r: st.image(img_r, caption=f"Rak {t['Kode_Lokasi']}")
    except: st.info("Sistem siap. Silakan upload data Excel Anda.")

# MODUL: UPLOAD CENTER
elif fitur == "Upload Center":
    st.subheader("🚀 Import Data Excel")
    file = st.file_uploader("Upload Excel", type=["xlsx"])
    if file and st.button("Proses Import"):
        df_up = pd.read_excel(file)
        # Deteksi tabel tujuan
        target = "stok_toko" if "Nama_Barang" in df_up.columns else "master_lokasi"
        df_up.to_sql(target, con=engine, if_exists="append", index=False)
        st.success(f"Berhasil! Data masuk ke tabel {target}")

# MODUL: KALIBRASI
elif fitur == "Kalibrasi":
    st.subheader("🎯 Kalibrasi Koordinat")
    # ... (Kode kalibrasi klik tetap sama dengan v3.8)
    st.write("Silakan pilih rak dan klik pada peta untuk menyimpan koordinat baru.")
