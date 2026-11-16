# ============================================================
# SIM-PETANI SUMATERA UTARA
# GOVERNMENT AGRICULTURAL DATA DASHBOARD
# ============================================================
# Database : Neon PostgreSQL
# Source   : DB_PUSAT_SUMUT
# Warehouse: DW_SUMUT
# Framework: Streamlit
# ============================================================


# ============================================================
# 1. IMPORT LIBRARY
# ============================================================

import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import logging


# ============================================================
# 2. KONFIGURASI WEBSITE
# ============================================================

st.set_page_config(
    page_title="SIM-PETANI SUMUT",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Logging untuk pemeriksaan error di Streamlit Cloud
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sim_petani_sumut")


# ============================================================
# 3. DESAIN WEBSITE
# ============================================================

st.markdown("""
<style>

.stApp {
    background-color: #f5f7fa;
}

[data-testid="stMetric"] {
    background-color: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
}

[data-testid="stSidebar"] {
    background-color: #eaf0f6;
}

h1 {
    color: #153653;
}

h2, h3 {
    color: #214b68;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# 4. KONFIGURASI KONEKSI DATABASE
# ============================================================

def get_database_url():

    try:
        database_url = st.secrets["database"]["url"]

        if not database_url:
            raise ValueError("URL database kosong.")

        return database_url

    except Exception:
        st.error(
            "Konfigurasi database belum tersedia. "
            "Periksa Settings > Secrets di Streamlit Cloud."
        )
        st.stop()


# ============================================================
# 5. FUNGSI MEMBACA DATA POSTGRESQL
# ============================================================

def read_data(query, params=None):

    conn = None

    try:

        # Membuat koneksi baru setiap query.
        # Tidak menggunakan cache_resource untuk koneksi.

        conn = psycopg2.connect(
            get_database_url(),
            connect_timeout=20,
            sslmode="require",
            application_name="SIM_PETANI_SUMUT"
        )

        with conn.cursor() as cur:

            cur.execute(query, params or ())

            rows = cur.fetchall()

            columns = [
                description[0]
                for description in cur.description
            ]

        df = pd.DataFrame(
            rows,
            columns=columns
        )

        return df

    except psycopg2.Error as error:

        logger.exception(
            "Kesalahan PostgreSQL ketika membaca data."
        )

        st.error(
            "Gagal mengambil data dari database PostgreSQL."
        )

        st.info(
            "Periksa koneksi Neon, nama database, "
            "hak akses user, schema, dan SQL query."
        )

        st.stop()

    except Exception:

        logger.exception(
            "Kesalahan aplikasi ketika membaca data."
        )

        st.error(
            "Terjadi kesalahan ketika memproses data."
        )

        st.stop()

    finally:

        if conn is not None and not conn.closed:
            conn.close()


# ============================================================
# 6. HEADER WEBSITE
# ============================================================

st.title("🌾 SIM-PETANI SUMATERA UTARA")

st.markdown("""
### Sistem Informasi Pemetaan Petani dan Penyuluh

**Provinsi Sumatera Utara**

Government Agricultural Data Dashboard

Platform integrasi data pertanian kabupat
