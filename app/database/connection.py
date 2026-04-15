import os
import socket
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Ambil Database URL dari env
DATABASE_URL = os.getenv("DATABASE_URL")

# Konfigurasi engine yang disesuaikan untuk lingkungan Serverless (Vercel)
engine = create_engine(
    DATABASE_URL,
    pool_size=1,            # Mencegah pembukaan koneksi berlebih
    max_overflow=0,         # Membatasi koneksi agar tidak melebihi kapasitas
    pool_timeout=30,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()