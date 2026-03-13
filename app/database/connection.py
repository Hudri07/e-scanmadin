import os
import socket
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# --- PATCH PAKSA IPv4 (HANYA UNTUK VERCEL) ---
# Memastikan sistem tidak menggunakan IPv6 saat melakukan resolve host Supabase
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    # Filter hanya mengambil AF_INET (IPv4)
    return [r for r in responses if r[0] == socket.AF_INET]

socket.getaddrinfo = new_getaddrinfo
# ---------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

# Konfigurasi engine yang disesuaikan untuk lingkungan Serverless (Vercel)
engine = create_engine(
    DATABASE_URL,
    pool_size=1,            # Mencegah pembukaan koneksi berlebih
    max_overflow=0,         # Membatasi koneksi agar tidak melebihi kapasitas
    pool_timeout=30,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()