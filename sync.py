import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px


# ==========================================
# 1. KONFIGURASI WEBSITE
# ==========================================

st.set_page_config(
    page_title="SIM-PETANI SUMUT",
    page_icon="🌾",
    layout="wide"
)

st.markdown("""
<style>
.main {
    background-color: #f5f7fa;
}

[data-testid="stMetric"] {
    background: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. KONEKSI DATABASE DATA WAREHOUSE
# ==========================================

import os
import streamlit as st

def get_database_url():

    # 1. Prioritaskan environment variable GitHub Actions
    database_url = os.getenv("DATAWAREHOUSE_URL")

    if database_url:
        return database_url

    # 2. Jika dijalankan di Streamlit Cloud,
    # gunakan konfigurasi Streamlit Secrets
    try:
        return st.secrets["datawarehouse"]["url"]

    except Exception as e:
        raise RuntimeError(
            "Koneksi Data Warehouse belum dikonfigurasi. "
            "Tambahkan DATAWAREHOUSE_URL pada GitHub Actions "
            "atau [datawarehouse].url pada Streamlit Secrets."
        ) from e


def read_data(query, params=None):

    conn = None

    try:

        database_url = get_database_url()

        conn = psycopg2.connect(
            database_url,
            connect_timeout=20,
            sslmode="require",
            application_name="SIM_PETANI_SUMUT"
        )

        with conn.cursor() as cur:

            cur.execute(query, params)

            # Mendapatkan nama kolom
            columns = [
                description[0]
                for description in cur.description
            ]

            # Mengambil data
            rows = cur.fetchall()

            # Mengubah hasil menjadi Pandas DataFrame
            df = pd.DataFrame(
                rows,
                columns=columns
            )

        return df

    except psycopg2.Error as e:

        st.error(
            f"Database Error: {type(e).__name__}: {e}"
        )

        raise

    except Exception as e:

        st.error(
            f"Application Error: {type(e).__name__}: {e}"
        )

        raise

    finally:

        if conn is not None:
            conn.close()


# ==========================================
# 3. HEADER
# ==========================================

st.title("🌾 SIM-PETANI SUMATERA UTARA")

st.markdown("""
**Sistem Informasi Pemetaan Petani dan Penyuluh
Provinsi Sumatera Utara**

Government Agricultural Data Dashboard
""")

st.divider()


# ==========================================
# 4. AMBIL TANGGAL SNAPSHOT
# ==========================================

dates = read_data("""
    SELECT DISTINCT id_tanggal
    FROM dw.fact_petani_harian
    ORDER BY id_tanggal DESC
""")

if dates.empty:

    st.warning(
        "Belum terdapat data pada Data Warehouse."
    )

    st.stop()


date_options = dates["id_tanggal"].tolist()

selected_date = st.sidebar.selectbox(
    "Pilih Tanggal Snapshot",
    date_options
)


# ==========================================
# 5. SIDEBAR NAVIGASI
# ==========================================

menu = st.sidebar.radio(
    "MENU NAVIGASI",
    [
        "Dashboard Utama",
        "Statistik Kabupaten",
        "Statistik Komoditas",
        "Data Petani"
    ]
)


# ==========================================
# 6. DASHBOARD UTAMA
# ==========================================

if menu == "Dashboard Utama":

    summary = read_data("""
        SELECT
            COUNT(*) AS total_petani,
            COALESCE(SUM(luas_lahan), 0) AS total_luas,
            COUNT(DISTINCT wilayah_sumber) AS total_kabupaten,
            COUNT(DISTINCT id_komoditas) AS total_komoditas
        FROM dw.fact_petani_harian
        WHERE id_tanggal = %s
    """, (selected_date,))

   
    if summary.empty or int(summary.iloc[0]["total_petani"]) == 0:
        st.warning("Data ringkasan tidak tersedia untuk tanggal yang dipilih.")

    else:
        row = summary.iloc[0]

        st.subheader("Ringkasan Data Petani")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total Petani",
            f'{int(row["total_petani"]):,}'
        )

        col2.metric(
            "Total Luas Lahan",
            f'{float(row["total_luas"]):,.2f} ha'
        )

        col3.metric(
            "Total Kabupaten",
            f'{int(row["total_kabupaten"]):,}'
        )
# ==========================================
# 7. STATISTIK KABUPATEN
# ==========================================

elif menu == "Statistik Kabupaten":

    df_kabupaten = read_data("""
        SELECT
            kabupaten,
            total_petani,
            total_luas_lahan
        FROM dw.vw_petani_kabupaten
        WHERE id_tanggal = %s
        ORDER BY total_petani DESC
    """, (selected_date,))

    st.subheader("Statistik Petani Berdasarkan Kabupaten")

    if df_kabupaten.empty:
        st.warning("Data statistik kabupaten tidak tersedia.")

    else:
        col1, col2 = st.columns(2)

        col1.metric(
            "Jumlah Kabupaten",
            len(df_kabupaten)
        )

        col2.metric(
            "Total Luas Lahan",
            f'{df_kabupaten["total_luas_lahan"].sum():,.2f} ha'
        )

        fig = px.bar(
            df_kabupaten.sort_values(
                "total_petani",
                ascending=True
            ),
            x="total_petani",
            y="kabupaten",
            orientation="h",
            title="Jumlah Petani per Kabupaten",
            labels={
                "total_petani": "Jumlah Petani",
                "kabupaten": "Kabupaten"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

        fig_luas = px.bar(
            df_kabupaten.sort_values(
                "total_luas_lahan",
                ascending=True
            ),
            x="total_luas_lahan",
            y="kabupaten",
            orientation="h",
            title="Luas Lahan per Kabupaten",
            labels={
                "total_luas_lahan": "Luas Lahan (Ha)",
                "kabupaten": "Kabupaten"
            }
        )

        st.plotly_chart(fig_luas, use_container_width=True)


# ==========================================
# 8. STATISTIK KOMODITAS
# ==========================================

elif menu == "Statistik Komoditas":

    df_komoditas = read_data("""
        SELECT
            nama_komoditas,
            SUM(total_petani) AS total_petani,
            SUM(total_luas_lahan) AS total_luas_lahan
        FROM dw.vw_petani_komoditas
        WHERE id_tanggal = %s
        GROUP BY nama_komoditas
        ORDER BY total_petani DESC
    """, (selected_date,))

    st.subheader("Statistik Petani Berdasarkan Komoditas")

    if df_komoditas.empty:
        st.warning("Data statistik komoditas tidak tersedia.")

    else:
        col1, col2 = st.columns(2)

        col1.metric(
            "Jumlah Komoditas",
            len(df_komoditas)
        )

        col2.metric(
            "Total Luas Lahan",
            f'{df_komoditas["total_luas_lahan"].sum():,.2f} ha'
        )

        fig = px.bar(
            df_komoditas,
            x="nama_komoditas",
            y="total_petani",
            title="Jumlah Petani Berdasarkan Komoditas",
            labels={
                "nama_komoditas": "Komoditas",
                "total_petani": "Jumlah Petani"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

        fig_luas = px.pie(
            df_komoditas,
            names="nama_komoditas",
            values="total_luas_lahan",
            title="Distribusi Luas Lahan Berdasarkan Komoditas",
            hole=0.4
        )

        st.plotly_chart(fig_luas, use_container_width=True)


# ==========================================
# 9. DATA PETANI
# ==========================================

elif menu == "Data Petani":

    df_petani = read_data("""
        SELECT
            f.kode_petani,
            f.nama_petani,
            w.kabupaten,
            w.desa,
            k.nama_komoditas,
            f.luas_lahan
        FROM dw.fact_petani_harian f
        LEFT JOIN dw.dim_wilayah w
            ON f.id_wilayah = w.id_wilayah
        LEFT JOIN dw.dim_komoditas k
            ON f.id_komoditas = k.id_komoditas
        WHERE f.id_tanggal = %s
        ORDER BY f.nama_petani
    """, (selected_date,))

    st.subheader("Data Petani Sumatera Utara")

    if df_petani.empty:
        st.warning("Data petani tidak tersedia.")

    else:
        search = st.text_input(
            "Cari nama atau kode petani"
        )

        col1, col2 = st.columns(2)

        daftar_kabupaten = [
            "Semua Kabupaten"
        ] + sorted(
            df_petani["kabupaten"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        daftar_komoditas = [
            "Semua Komoditas"
        ] + sorted(
            df_petani["nama_komoditas"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        with col1:
            kabupaten_pilih = st.selectbox(
                "Filter Kabupaten",
                daftar_kabupaten
            )

        with col2:
            komoditas_pilih = st.selectbox(
                "Filter Komoditas",
                daftar_komoditas
            )

        df_tampil = df_petani.copy()

        if search.strip():
            mask = (
                df_tampil["nama_petani"]
                .astype(str)
                .str.contains(search.strip(), case=False, na=False)
                |
                df_tampil["kode_petani"]
                .astype(str)
                .str.contains(search.strip(), case=False, na=False)
            )

            df_tampil = df_tampil[mask]

        if kabupaten_pilih != "Semua Kabupaten":
            df_tampil = df_tampil[
                df_tampil["kabupaten"] == kabupaten_pilih
            ]

        if komoditas_pilih != "Semua Komoditas":
            df_tampil = df_tampil[
                df_tampil["nama_komoditas"] == komoditas_pilih
            ]

        st.caption(
            f"Menampilkan {len(df_tampil)} dari {len(df_petani)} data petani."
        )

        st.dataframe(
            df_tampil,
            use_container_width=True,
            hide_index=True
        )
        col4.metric(
            "Total Komoditas",
            f'{int(row["total_komoditas"]):,}'
        )
