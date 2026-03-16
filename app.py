import streamlit as st
from sqlalchemy import create_engine, text

# --- DATA KONEKSI (Cek image_9c659d.png) ---
USER = "3oNapQCmXkUdxGF.root"
HOST = "gateway01.southeast-1.prod.aws.tidbcloud.com"
PORT = 4000
DB_NAME = "test"
# MASUKKAN PASSWORD HASIL GENERATE DI SINI
PASS = "ZsUvxG2dfGphBedY" 

st.title("🧪 TiDB Cloud Connection Test")

try:
    # Menggunakan konfigurasi paling stabil untuk cloud
    engine = create_engine(
        f"mysql+mysqlconnector://{USER}:{PASS}@{HOST}:{PORT}/{DB_NAME}",
        connect_args={
            "ssl_disabled": False,
            "use_pure": True, # Driver murni Python
            "connection_timeout": 30
        }
    )
    
    with engine.connect() as conn:
        # Mengetes koneksi paling dasar
        res = conn.execute(text("SELECT 1")).fetchone()
        if res:
            st.success("✅ MANTAP! Koneksi ke TiDB Cloud Berhasil.")
            st.balloons()
            st.write("Sekarang Bapak bisa mengembalikan skrip Navigasi v4.0 tadi.")
            
except Exception as e:
    st.error("❌ KONEKSI MASIH GAGAL")
    st.write(f"Detail Error: {e}")
    
    st.divider()
    st.write("### Checklist Perbaikan:")
    st.write("1. **Password**: Apakah Bapak memasukkan password login TiDB? Jika ya, ganti dengan password dari tombol **Generate Password**.")
    st.write("2. **IP Access**: Pastikan di TiDB sudah muncul rule `0.0.0.0/0` (Allow all public connections).")
    st.write("3. **Status Cluster**: Pastikan status Cluster0 adalah **Active**.")
