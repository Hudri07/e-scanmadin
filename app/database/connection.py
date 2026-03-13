import os
import socket
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Memaksa Python agar hanya menggunakan alamat IPv4 (AF_INET)
# untuk setiap koneksi ke database Supabase
def force_ipv4():
    def getaddrinfo(*args, **kwargs):
        # Memaksa agar hanya mengambil alamat IPv4
        return [r for r in socket.getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]
    socket.getaddrinfo = getaddrinfo

force_ipv4()
# ---------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

# Gunakan connect_args agar SQLAlchemy lebih patuh pada aturan SSL Supabase
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"}, 
    pool_size=10,
    max_overflow=2,
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
