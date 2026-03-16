import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from PIL import Image, ImageDraw
import requests
from io import BytesIO
from streamlit_image_coordinates import streamlit_image_coordinates

# --- 1. KONFIGURASI DATABASE (TIDB CLOUD) ---
# Data ini diambil dari parameter koneksi Cluster0 Bapak
USER = "3oNapQCmXkUdxGF.root"
HOST = "gateway01.southeast-1.prod.aws.tidbcloud.com"
PORT = "4000"
DB_NAME = "test"
# Masukkan password yang Bapak generate di dashboard TiDB
PASS = "ep1lKmgxXu6rlPIo" 

@st.cache_resource
def get_engine():
    # TiDB Cloud mewajibkan koneksi SSL
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
    # Ekstrak ID jika user memasukkan link lengkap
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

# Sidebar Navigasi
with st.sidebar:
    st.title("🏗️ GMB System")
    st.write(f"User: {USER}")
    st.divider()
    fitur = st.radio("Pilih Modul:", [
        "Peta Navigasi",
        "Dashboard & Stok",
        "Master Lokasi",
        "Kalibrasi Lokasi",
        "Upload Center"
    ])
    st.divider()
    st.caption("v3.7 - TiDB Cloud Online")

# --- MODUL 1: PETA NAVIGASI ---
if fitur == "Peta Navigasi":
    st.subheader("📍 Lokasi Barang di Gudang")
    try:
        # Join stok dan master lokasi untuk mendapatkan koordinat
        query = """
        SELECT s.Nama_Barang, s.Kode_Lokasi, l.lantai, l.x_coord, l.y_coord, l.url_gambar 
        FROM stok_toko s 
        JOIN master_lokasi l ON s.Kode_Lokasi = l.lokasi
        """
        df_nav = pd.read_sql(query, con=engine)
        
        selected_item = st.selectbox("Cari Barang:", sorted(df_nav['Nama_Barang'].unique()))
        target = df_nav[df_nav['Nama_Barang'] == selected_item].iloc[0]
        
        st.info(f"📍 Posisi: **{target['Kode_Lokasi']}** | Lantai: **{target['lantai']}**")
        
        col_peta, col_foto = st.columns([2, 1])
        
        with col_peta:
            # Ambil denah dari tabel peta_lantai
            q_p = text("SELECT url_peta FROM peta_lantai WHERE nama_lantai = :lt")
            with engine.connect() as conn:
                res_p = conn.execute(q_p, {"lt": target['lantai']}).fetchone()
            
            if res_p:
                img_map = get_image_from_drive(res_p[0])
                if img_map:
                    img_map = img_map.convert("RGB")
                    draw = ImageDraw.Draw(img_map)
                    x, y = target['x_coord'], target['y_coord']
                    # Gambar titik indikator lokasi
                    draw.ellipse((x-30, y-30, x+30, y+30), fill="red", outline="white", width=8)
                    st.image(img_map, use_container_width=True)
            else:
                st.warning("Denah peta belum tersedia.")

        with col_foto:
            st.write("### 📸 Foto Rak")
            img_rak = get_image_from_drive(target['url_gambar'])
            if img_rak:
                st.image(img_rak, caption=f"Kondisi Rak {target['Kode_Lokasi']}", use_container_width=True)
            else:
                st.warning("Foto rak belum ada.")

    except Exception as e:
        st.error(f"Gagal memuat navigasi: {e}")

# --- MODUL 2: DASHBOARD & STOK ---
elif fitur == "Dashboard & Stok":
    st.subheader("📊 Monitoring Stok Real-time")
    try:
        df_stok = pd.read_sql("SELECT * FROM stok_toko", con=engine)
        search_stok = st.text_input("🔍 Cari Barang atau Brand:")
        if search_stok:
            df_stok = df_stok[df_stok.apply(lambda r: r.astype(str).str.contains(search_stok, case=False).any(), axis=1)]
        st.dataframe(df_stok, use_container_width=True)
    except Exception as e:
        st.error(f"Error Database: {e}")

# --- MODUL 3: MASTER LOKASI (SEARCH & UPDATE) ---
elif fitur == "Master Lokasi":
    st.subheader("📍 Management Master Lokasi")
    try:
        df_master = pd.read_sql("SELECT * FROM master_lokasi", con=engine)
        
        col_list, col_upd = st.columns([2, 1])
        
        with col_list:
            find_loc = st.text_input("🔍 Cari Kode Rak (Contoh: D1068):")
            if find_loc:
                df_show = df_master[df_master['lokasi'].str.contains(find_loc, case=False, na=False)]
            else:
                df_show = df_master.head(20)
            st.dataframe(df_show, use_container_width=True)

        with col_upd:
            if find_loc and not df_show.empty:
                current_row = df_show.iloc[0]
                st.markdown(f"**Edit Foto Rak: {current_row['lokasi']}**")
                new_url = st.text_input("ID/Link Drive Baru:", value=str(current_row['url_gambar'] or ""))
                
                if st.button("💾 Simpan Perubahan"):
                    q_upd = text("UPDATE master_lokasi SET url_gambar = :url WHERE lokasi = :loc")
                    with engine.begin() as conn:
                        conn.execute(q_upd, {"url": new_url, "loc": current_row['lokasi']})
                    st.success("Berhasil Update!")
                    st.rerun()
                
                # Preview kecil
                if new_url:
                    prev = get_image_from_drive(new_url)
                    if prev: st.image(prev, use_container_width=True)
    except Exception as e:
        st.error(str(e))

# --- MODUL 4: KALIBRASI LOKASI ---
elif fitur == "Kalibrasi Lokasi":
    st.subheader("🎯 Kalibrasi Titik Rak")
    try:
        df_locs = pd.read_sql("SELECT lokasi, lantai, x_coord, y_coord FROM master_lokasi", con=engine)
        sel_rak = st.selectbox("Pilih Rak untuk Dikalibrasi:", df_locs['lokasi'].unique())
        rak_data = df_locs[df_locs['lokasi'] == sel_rak].iloc[0]

        q_map = text("SELECT url_peta FROM peta_lantai WHERE nama_lantai = :lt")
        with engine.connect() as conn:
            map_res = conn.execute(q_map, {"lt": rak_data['lantai']}).fetchone()
        
        if map_res:
            img_c = get_image_from_drive(map_res[0])
            if img_c:
                st.info("Klik tepat pada lokasi rak di gambar bawah ini.")
                coords = streamlit_image_coordinates(img_c, key="calibration_tool")
                
                # Gunakan koordinat klik atau data lama
                cx = coords["x"] if coords else (rak_data['x_coord'] or 0)
                cy = coords["y"] if coords else (rak_data['y_coord'] or 0)
                
                c_x, c_y, c_btn = st.columns(3)
                final_x = c_x.number_input("Koordinat X:", value=int(cx))
                final_y = c_y.number_input("Koordinat Y:", value=int(cy))
                
                if c_btn.button("💾 Simpan Koordinat Baru", use_container_width=True):
                    # Perbaikan: Menggunakan text() untuk membungkus query
                    sql_save = text("UPDATE master_lokasi SET x_coord = :x, y_coord = :y WHERE lokasi = :loc")
                    with engine.begin() as conn:
                        conn.execute(sql_save, {"x": final_x, "y": final_y, "loc": sel_rak})
                    st.success(f"Rak {sel_rak} berhasil dikalibrasi!")
                    st.rerun()
    except Exception as e:
        st.error(f"Gagal Kalibrasi: {e}")

# --- MODUL 5: UPLOAD CENTER ---
elif fitur == "Upload Center":
    st.subheader("🚀 Upload Data Gudang (Excel)")
    uploaded_file = st.file_uploader("Pilih file .xlsx", type=["xlsx"])
    if uploaded_file and st.button("🚀 Mulai Import ke Cloud"):
        try:
            df_up = pd.read_excel(uploaded_file)
            # Normalisasi nama kolom
            if 'QtyStok' in df_up.columns: df_up = df_up.rename(columns={'QtyStok': 'Qty_St_ok'})
            
            target_table = 'stok_toko' if 'Nama_Barang' in df_up.columns else 'master_lokasi'
            df_up.to_sql(target_table, con=engine, if_exists='append', index=False)
            st.success(f"Berhasil mengunggah data ke tabel {target_table} di TiDB Cloud!")
        except Exception as e:
            st.error(f"Gagal Import: {e}")
