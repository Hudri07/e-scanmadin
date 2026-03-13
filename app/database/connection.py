import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

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
