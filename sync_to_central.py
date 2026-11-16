import os
import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
# Nama database sumber dan label wilayah yang akan dicatat di pusat.
SOURCES = [
    ("DB_KARO", "KARO"),
    ("DB_DELI_SERDANG", "DELI SERDANG"),
    ("DB_LANGKAT", "LANGKAT"),
]
SOURCE_SCHEMA = "public"
SOURCE_TABLE = "petani"
TARGET_SCHEMA = "public"
TARGET_TABLE = "petani_pusat"
SOURCE_COLUMNS = [
    "kode_petani", "nama_petani", "desa",
    "komoditas", "luas_lahan", "updated_at"
]
TARGET_COLUMNS = [
    "kode_petani", "nama_petani", "desa",
    "komoditas", "luas_lahan", "wilayah_sumber", "updated_at"
]
def connect_from_env(secret_name):
    url = os.getenv(secret_name)
    if not url:
        raise RuntimeError(f"GitHub Secret {secret_name} belum diatur.")
    return psycopg2.connect(url, connect_timeout=15)
def extract_region(secret_name, region_name):
    rows = []
    conn = connect_from_env(secret_name)
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT {} FROM {}.{}").format(
                    sql.SQL(", ").join(map(sql.Identifier, SOURCE_COLUMNS)),
                    sql.Identifier(SOURCE_SCHEMA),
                    sql.Identifier(SOURCE_TABLE),
                )
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    if not rows:
        raise RuntimeError(
            f"Tidak ada data ditemukan pada sumber {region_name}. "
            "Proses dibatalkan agar data pusat tidak terhapus."
        )
    # Validasi kode petani unik di dalam masing-masing wilayah.
    codes = [row[0] for row in rows]
    if len(codes) != len(set(codes)):
        raise RuntimeError(f"Ada kode_petani duplikat di wilayah {region_name}.")
    output = []
    for row in rows:
        if row[0] is None or row[1] is None:
            raise RuntimeError(
                f"kode_petani/nama_petani kosong pada wilayah {region_name}."
            )
        area = row[4]
        if area is not None and area < 0:
            raise RuntimeError(f"luas_lahan negatif pada wilayah {region_name}.")
        output.append(tuple(row)[:5] + (region_name, row[5]))
    print(f"{region_name}: {len(output)} baris berhasil dibaca.")
    return output
def main():
    # Baca semua sumber terlebih dahulu. Jika salah satu gagal,
    # database pusat belum disentuh. 
   all_rows = []
    expected_regions = []
    for secret_name, region_name in SOURCES:
        region_rows = extract_region(secret_name, region_name)
        all_rows.extend(region_rows)
        expected_regions.append(region_name)
    # Refresh hanya wilayah yang dikelola skrip ini, dalam satu transaksi.
    # Jika insert gagal, DELETE juga dibatalkan oleh rollback.
    conn = connect_from_env("DB_PUSAT")
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DELETE FROM {}.{} WHERE wilayah_sumber = ANY(%s)").format(
                        sql.Identifier(TARGET_SCHEMA),
                        sql.Identifier(TARGET_TABLE),
                    ),
                    (expected_regions,),
                )
                insert_query = sql.SQL("INSERT INTO {}.{} ({}) VALUES %s").format(
                    sql.Identifier(TARGET_SCHEMA),
                    sql.Identifier(TARGET_TABLE),
                    sql.SQL(", ").join(map(sql.Identifier, TARGET_COLUMNS)),
                )
                execute_values(cur, insert_query.as_string(conn), all_rows)
        print("Sinkronisasi berhasil.")
        print(f"Total baris dikirim ke pusat: {len(all_rows)}")
        for region in expected_regions:
            count = sum(1 for row in all_rows if row[5] == region)
            print(f"{region}: {count} baris")
    finally:
        conn.close()
if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
