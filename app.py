import streamlit as st
from sqlalchemy import create_engine, text

# Detail dari dashboard Cluster0 Bapak
USER = "3oNapQCmXkUdxGF.root"
HOST = "gateway01.ap-southeast-1.prod.aws.tidbcloud.com"
PORT = 4000
DB_NAME = "test"
# MASUKKAN PASSWORD BARU BAPAK DI SINI
PASS = "ISI_DENGAN_PASSWORD_RESET_TERAKHIR" 

st.set_page_config(page_title="GMB System Check")
st.title("🏗️ GMB System - Cloud Status")

@st.cache_resource
def check_cloud():
    try:
        # Konfigurasi paling aman untuk Streamlit Cloud
        engine = create_engine(
            f"mysql+mysqlconnector://{USER}:{PASS}@{HOST}:{PORT}/{DB_NAME}",
            connect_args={
                "ssl_disabled": False,
                "use_pure": True,
                "connection_timeout": 30
            }
        )
        with engine.connect() as conn:
            # Tes apakah database bisa merespon
            conn.execute(text("SELECT 1"))
        return engine, None
    except Exception as e:
        return None, str(e)

engine, err = check_cloud()

if engine:
    st.success("✅ KONEKSI CLOUD AKTIF!")
    st.balloons()
    
    # Cek apakah tabel sudah ada
    with engine.connect() as conn:
        res = conn.execute(text("SHOW TABLES"))
        tables = [row[0] for row in res]
        st.write("Tabel yang terdeteksi:", tables)
        
    st.info("Jika tabel sudah muncul, Bapak bisa kembali menggunakan skrip navigasi penuh.")
else:
    st.error("❌ KONEKSI MASIH TERPUTUS")
    st.write(f"Detail kendala: {err}")
    st.warning("Pastikan IP Access List 0.0.0.0/0 sudah tersimpan (Save) di dashboard.")
