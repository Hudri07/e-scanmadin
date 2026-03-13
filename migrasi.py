import sqlite3
import urllib.parse
import json
from sqlalchemy import create_engine, text

# --- 1. KONFIGURASI SUPABASE ---
DB_USER = "postgres"
DB_NAME = "postgres"
DB_HOST = "db.sooofmcfmpxmrpufkylv.supabase.co"
DB_PORT = "6543"
DB_PASS = "BisaAjaloh123**" 

safe_password = urllib.parse.quote_plus(DB_PASS)
SUPABASE_URL = f"postgresql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
pg_engine = create_engine(SUPABASE_URL)

# --- 2. KONEKSI SQLITE LOKAL ---
sqlite_conn = sqlite3.connect('data/madin.db')
sqlite_cursor = sqlite_conn.cursor()

def migrate_all():
    print("🚀 Memulai Migrasi Total ke Supabase...")

    with pg_engine.connect() as pg_conn:
        
        # --- A. TABEL USERS ---
        print("👥 Memindahkan data Users...")
        sqlite_cursor.execute("SELECT username, email, full_name, hashed_password, disabled FROM users")
        for row in sqlite_cursor.fetchall():
            query = text("""
                INSERT INTO users (username, email, full_name, hashed_password, disabled) 
                VALUES (:u, :e, :f, :h, :d) ON CONFLICT (username) DO NOTHING
            """)
            pg_conn.execute(query, {"u":row[0], "e":row[1], "f":row[2], "h":row[3], "d":bool(row[4])})

        # --- B. TABEL SISWA ---
        print("📦 Memindahkan data Siswa...")
        sqlite_cursor.execute("SELECT nomor_peserta, nama, kelas FROM siswa")
        for row in sqlite_cursor.fetchall():
            query = text("INSERT INTO siswa (nomor_peserta, nama, kelas) VALUES (:no, :nama, :kls) ON CONFLICT (nomor_peserta) DO NOTHING")
            pg_conn.execute(query, {"no": row[0], "nama": row[1], "kls": row[2]})
        
        # --- C. TABEL KUNCI JAWABAN ---
        print("🔑 Memindahkan data Kunci Jawaban...")
        sqlite_cursor.execute("SELECT mapel, kelas, kunci_json FROM kunci_jawaban")
        for row in sqlite_cursor.fetchall():
            query = text("INSERT INTO kunci_jawaban (mapel, kelas, kunci_json) VALUES (:mpl, :kls, :kunci) ON CONFLICT (mapel, kelas) DO NOTHING")
            pg_conn.execute(query, {"mpl": row[0], "kls": row[1], "kunci": row[2]})

        # --- D. TABEL HASIL UJIAN ---
        print("📊 Memindahkan data Hasil Ujian...")
        # Sesuaikan kolomnya: nomor_peserta, mapel, skor, tanggal
        sqlite_cursor.execute("SELECT nomor_peserta, mapel, skor, tanggal FROM hasil_ujian")
        for row in sqlite_cursor.fetchall():
            query = text("""
                INSERT INTO hasil_ujian (nomor_peserta, mapel, skor, tanggal) 
                VALUES (:no, :mpl, :skr, :tgl) 
                ON CONFLICT (nomor_peserta, mapel) DO NOTHING
            """)
            pg_conn.execute(query, {"no": row[0], "mpl": row[1], "skr": row[2], "tgl": row[3]})

        pg_conn.commit()
    
    print("✅ SEMUA DATA BERHASIL DIPINDAHKAN!")

if __name__ == "__main__":
    migrate_all()
    sqlite_conn.close()