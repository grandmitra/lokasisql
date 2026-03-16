import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from PIL import Image, ImageDraw
import requests
from io import BytesIO
from streamlit_image_coordinates import streamlit_image_coordinates

# --- 1. KONFIGURASI DATABASE (TIDB CLOUD) ---
# Data berdasarkan parameter Cluster0 Bapak
USER = "3oNapQCmXkUdxGF.root"
HOST = "gateway01.southeast-1.prod.aws.tidbcloud.com"
PORT = "4000"
DB_NAME = "test"
# Gunakan password yang Bapak buat melalui tombol "Generate Password"
PASS = "ep1lKmgxXu6rlPIo" 

@st.cache_resource
def get_engine():
    # Mengaktifkan SSL untuk koneksi cloud yang aman
    return create_engine(
        f"mysql+mysqlconnector://{USER}:{PASS}@{HOST}:{PORT}/{DB_NAME}",
        connect_args={"ssl_disabled": False},
        pool_pre_ping=True
    )

engine = get_engine()

# --- 2. FUNGSI PENDUKUNG GAMBAR ---
def get_image_from_drive(file_id):
    if not file_id or str(file_id).lower() in ['null', 'none', ''] or len(str(file_id)) < 5: 
        return None
    clean_id = str(file_id).split('id=')[-1].split('/')[-1].split('?')[0]
    url = f"https://drive.google.com/uc?export=download&id={clean_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except:
        return None
    return None

# --- 3. UI CONFIGURATION ---
st.set_page_config(page_title="GMB Integrated System", layout="wide")

with st.sidebar:
    st.title("🏗️ GMB System")
    st.write(f"Database: TiDB Cloud")
    st.divider()
    fitur = st.radio("Pilih Modul:", [
        "Peta Navigasi",
        "Dashboard & Stok",
        "Master Lokasi",
        "Kalibrasi Lokasi",
        "Upload Center"
    ])
    st.divider()
    st.caption("v3.8 - Fix Executable Object & SSL")

# --- MODUL 1: PETA NAVIGASI ---
if fitur == "Peta Navigasi":
    st.subheader("📍 Lokasi Barang")
    try:
        query = text("""
            SELECT s.Nama_Barang, s.Kode_Lokasi, l.lantai, l.x_coord, l.y_coord, l.url_gambar 
            FROM stok_toko s 
            JOIN master_lokasi l ON s.Kode_Lokasi = l.lokasi
        """)
        df_nav = pd.read_sql(query, con=engine)
        
        # Contoh pencarian barang seperti GAGANG PACUL
        selected_item = st.selectbox("Pilih Barang:", sorted(df_nav['Nama_Barang'].unique()))
        target = df_nav[df_nav['Nama_Barang'] == selected_item].iloc[0]
        
        st.success(f"📍 Lokasi: **{target['Kode_Lokasi']}** | **{target['lantai']}**")
        
        col_peta, col_foto = st.columns([2, 1])
        
        with col_peta:
            q_p = text("SELECT url_peta FROM peta_lantai WHERE nama_lantai = :lt")
            with engine.connect() as conn:
                res_p = conn.execute(q_p, {"lt": target['lantai']}).fetchone()
            
            if res_p:
                img_map = get_image_from_drive(res_p[0])
                if img_map:
                    img_map = img_map.convert("RGB")
                    draw = ImageDraw.Draw(img_map)
                    x, y = target['x_coord'], target['y_coord']
                    # Titik indikator merah di denah 3D
                    draw.ellipse((x-30, y-30, x+30, y+30), fill="red", outline="white", width=8)
                    st.image(img_map, use_container_width=True)
            else:
                st.warning("Denah peta belum tersedia di database.")

        with col_foto:
            st.write("### Foto Fisik Rak")
            img_rak = get_image_from_drive(target['url_gambar'])
            if img_rak:
                st.image(img_rak, use_container_width=True)
            else:
                st.warning("Foto rak belum ada.")

    except Exception as e:
        st.error(f"Error: {e}")

# --- MODUL 3: MASTER LOKASI (SEARCH & UPDATE) ---
elif fitur == "Master Lokasi":
    st.subheader("📍 Master Lokasi & Update Foto")
    try:
        df_master = pd.read_sql(text("SELECT * FROM master_lokasi"), con=engine)
        search_loc = st.text_input("🔍 Cari Kode Rak (Contoh: D1068):")
        
        if search_loc:
            df_display = df_master[df_master['lokasi'].str.contains(search_loc, case=False, na=False)]
        else:
            df_display = df_master.head(10)
        
        col_tabel, col_edit = st.columns([2, 1])
        with col_tabel:
            st.dataframe(df_display, use_container_width=True)
        
        with col_edit:
            if search_loc and not df_display.empty:
                row = df_display.iloc[0]
                st.write(f"**Edit Foto Rak: {row['lokasi']}**")
                new_url = st.text_input("Link Drive Baru:", value=str(row['url_gambar'] or ""))
                if st.button("💾 Simpan Gambar"):
                    q_upd = text("UPDATE master_lokasi SET url_gambar = :url WHERE lokasi = :loc")
                    with engine.begin() as conn:
                        conn.execute(q_upd, {"url": new_url, "loc": row['lokasi']})
                    st.success("Foto diperbarui!")
                    st.rerun()

    except Exception as e:
        st.error(str(e))

# --- MODUL 4: KALIBRASI LOKASI (FIX ERROR EXECUTABLE) ---
elif fitur == "Kalibrasi Lokasi":
    st.subheader("🎯 Kalibrasi Posisi Rak")
    try:
        df_cal = pd.read_sql(text("SELECT lokasi, lantai, x_coord, y_coord FROM master_lokasi"), con=engine)
        sel_rak = st.selectbox("Pilih Rak:", df_cal['lokasi'].unique())
        data_rak = df_cal[df_cal['lokasi'] == sel_rak].iloc[0]

        q_map = text("SELECT url_peta FROM peta_lantai WHERE nama_lantai = :lt")
        with engine.connect() as conn:
            map_data = conn.execute(q_map, {"lt": data_rak['lantai']}).fetchone()
        
        if map_data:
            img_c = get_image_from_drive(map_data[0])
            if img_c:
                st.info("Klik pada peta untuk mengambil koordinat.")
                value = streamlit_image_coordinates(img_c, key="cal_tool")
                
                # Koordinat dari klik atau data lama
                v_x = value["x"] if value else (data_rak['x_coord'] or 0)
                v_y = value["y"] if value else (data_rak['y_coord'] or 0)
                
                c1, c2, c3 = st.columns(3)
                final_x = c1.number_input("Koordinat X:", value=int(v_x))
                final_y = c2.number_input("Koordinat Y:", value=int(v_y))
                
                if c3.button("💾 Simpan Lokasi Baru", use_container_width=True):
                    # FIX: Menggunakan text() agar tidak error 'Not an executable object'
                    upd_sql = text("UPDATE master_lokasi SET x_coord = :x, y_coord = :y WHERE lokasi = :loc")
                    with engine.begin() as conn:
                        conn.execute(upd_sql, {"x": final_x, "y": final_y, "loc": sel_rak})
                    st.success(f"Lokasi {sel_rak} disimpan ke Cloud!")
                    st.rerun()
    except Exception as e:
        st.error(f"Gagal Kalibrasi: {e}")

# --- MODUL LAIN (Dashboard & Upload) ---
elif fitur == "Dashboard & Stok":
    st.subheader("📊 Monitoring Stok")
    df_stok = pd.read_sql(text("SELECT * FROM stok_toko"), con=engine)
    st.dataframe(df_stok, use_container_width=True)

elif fitur == "Upload Center":
    st.subheader("🚀 Import Data ke TiDB Cloud")
    up_file = st.file_uploader("Pilih file .xlsx", type=["xlsx"])
    if up_file and st.button("Proses Import"):
        df_up = pd.read_excel(up_file)
        if 'QtyStok' in df_up.columns: df_up = df_up.rename(columns={'QtyStok': 'Qty_St_ok'})
        target = 'stok_toko' if 'Nama_Barang' in df_up.columns else 'master_lokasi'
        df_up.to_sql(target, con=engine, if_exists='append', index=False)
        st.success("Data berhasil masuk ke Cloud!")
