import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from PIL import Image, ImageDraw
import requests
from io import BytesIO
from streamlit_image_coordinates import streamlit_image_coordinates

# --- 1. KONFIGURASI DATABASE TIDB CLOUD ---
# Masukkan detail dari dashboard TiDB Cloud Bapak
USER = "3oNapQCmXkUdxGF.root"
HOST = "gateway01.southeast-1.prod.aws.tidbcloud.com"
PORT = "4000"
DB_NAME = "test"
PASS = "ep1lKmgxXu6rlPIo" 

# Engine khusus TiDB Cloud (SSL diaktifkan)
engine = create_engine(
    f"mysql+mysqlconnector://{USER}:{PASS}@{HOST}:{PORT}/{DB_NAME}",
    connect_args={"ssl_disabled": False}
)

# --- 2. FUNGSI PENDUKUNG ---
def get_image_from_drive(file_id):
    if not file_id or str(file_id).lower() in ['null', 'none', ''] or len(str(file_id)) < 5: 
        return None
    # Membersihkan ID jika yang dimasukkan adalah link lengkap
    clean_id = str(file_id).split('id=')[-1].split('/')[-1].split('?')[0]
    url = f"https://drive.google.com/uc?export=download&id={clean_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except:
        return None
    return None

# --- 3. UI STREAMLIT ---
st.set_page_config(page_title="GMB Online System", layout="wide")

with st.sidebar:
    st.header("GMB Integrated")
    fitur = st.radio("Menu:", ["Master Lokasi", "Kalibrasi Lokasi", "Dashboard & Stok", "Peta Navigasi"])
    st.divider()
    st.info("Status: Connected to TiDB Cloud")

# --- MODUL: MASTER LOKASI (DENGAN PENCARIAN & UPDATE FOTO) ---
if fitur == "Master Lokasi":
    st.subheader("📍 Master Lokasi & Update Foto")
    try:
        df_master = pd.read_sql("SELECT * FROM master_lokasi", con=engine)
        
        col_list, col_edit = st.columns([2, 1])
        
        with col_list:
            search = st.text_input("🔍 Cari Kode Rak (misal: D1068):")
            if search:
                df_display = df_master[df_master['lokasi'].str.contains(search, case=False, na=False)]
            else:
                df_display = df_master.head(10)
            st.dataframe(df_display, use_container_width=True)

        with col_edit:
            if search and not df_display.empty:
                row = df_display.iloc[0]
                st.markdown(f"### Update Rak {row['lokasi']}")
                new_img_id = st.text_input("ID/Link Google Drive Baru:", value=str(row['url_gambar'] or ""))
                
                if st.button("💾 Simpan Perubahan"):
                    upd_query = text("UPDATE master_lokasi SET url_gambar = :url WHERE lokasi = :loc")
                    with engine.begin() as conn:
                        conn.execute(upd_query, {"url": new_img_id, "loc": row['lokasi']})
                    st.success("Foto berhasil diperbarui!")
                    st.rerun()
                
                # Preview Foto
                img_prev = get_image_from_drive(new_img_id)
                if img_prev: st.image(img_prev, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

# --- MODUL: KALIBRASI (FIX SQL OBJECT) ---
elif fitur == "Kalibrasi Lokasi":
    st.subheader("🎯 Kalibrasi Titik")
    try:
        df_c = pd.read_sql("SELECT lokasi, lantai, x_coord, y_coord FROM master_lokasi", con=engine)
        target = st.selectbox("Pilih Rak:", df_c['lokasi'].unique())
        curr_data = df_c[df_c['lokasi'] == target].iloc[0]

        q_peta = text("SELECT url_peta FROM peta_lantai WHERE nama_lantai = :lt")
        with engine.connect() as conn:
            p_res = conn.execute(q_peta, {"lt": curr_data['lantai']}).fetchone()
        
        if p_res:
            img_cal = get_image_from_drive(p_res[0])
            if img_cal:
                st.caption("Klik pada peta untuk menentukan posisi rak.")
                val = streamlit_image_coordinates(img_cal, key="cal_online")
                
                v_x = val["x"] if val else (curr_data['x_coord'] or 0)
                v_y = val["y"] if val else (curr_data['y_coord'] or 0)
                
                c1, c2, c3 = st.columns(3)
                final_x = c1.number_input("X:", value=int(v_x))
                final_y = c2.number_input("Y:", value=int(v_y))
                
                if c3.button("💾 Simpan Koordinat", use_container_width=True):
                    save_q = text("UPDATE master_lokasi SET x_coord = :x, y_coord = :y WHERE lokasi = :loc")
                    with engine.begin() as conn:
                        conn.execute(save_q, {"x": final_x, "y": final_y, "loc": target})
                    st.success("Koordinat diperbarui di Cloud!")
                    st.rerun()
    except Exception as e:
        st.error(str(e))

# --- MODUL: DASHBOARD & STOK ---
elif fitur == "Dashboard & Stok":
    st.subheader("📊 Monitoring Stok")
    try:
        df_stok = pd.read_sql("SELECT * FROM stok_toko", con=engine)
        cari_brg = st.text_input("🔍 Cari Nama Barang/Brand:")
        if cari_brg:
            df_stok = df_stok[df_stok.apply(lambda r: r.astype(str).str.contains(cari_brg, case=False).any(), axis=1)]
        st.dataframe(df_stok, use_container_width=True)
    except Exception as e:
        st.error(str(e))

# --- MODUL: PETA NAVIGASI ---
elif fitur == "Peta Navigasi":
    st.subheader("📍 Navigasi Gudang")
    try:
        q_nav = "SELECT s.Nama_Barang, s.Kode_Lokasi, l.lantai, l.x_coord, l.y_coord, l.url_gambar FROM stok_toko s JOIN master_lokasi l ON s.Kode_Lokasi = l.lokasi"
        df_nav = pd.read_sql(q_nav, con=engine)
        pilih = st.selectbox("Cari Barang:", sorted(df_nav['Nama_Barang'].unique()))
        t = df_nav[df_nav['Nama_Barang'] == pilih].iloc[0]
        
        st.info(f"Lokasi: {t['Kode_Lokasi']} | {t['lantai']}")
        
        col_map, col_img = st.columns([2, 1])
        with col_map:
            q_p = text("SELECT url_peta FROM peta_lantai WHERE nama_lantai = :lt")
            with engine.connect() as conn:
                p_url = conn.execute(q_p, {"lt": t['lantai']}).fetchone()
            
            img_map = get_image_from_drive(p_url[0]) if p_url else None
            if img_map:
                draw = ImageDraw.Draw(img_map)
                draw.ellipse((t['x_coord']-30, t['y_coord']-30, t['x_coord']+30, t['y_coord']+30), fill="red", outline="white", width=8)
                st.image(img_map, use_container_width=True)

        with col_img:
            img_rak = get_image_from_drive(t['url_gambar'])
            if img_rak: st.image(img_rak, caption=f"Foto Rak {t['Kode_Lokasi']}")
            else: st.warning("Foto rak belum diupload.")
    except Exception as e:
        st.error(str(e))
