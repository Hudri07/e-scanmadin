import os
from dotenv import load_dotenv

# Load file .env 
load_dotenv() 

# Pastikan URL terbaca
print(f"DEBUG: URL Database adalah -> {os.getenv('DATABASE_URL')}")

from app.database.connection import SessionLocal, engine 
from app.database.models import Base, UserTable 
from app.core.security import get_password_hash 

def create_initial_admin():
    # Membuat tabel di database (Neon/Postgres)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Cek apakah user admin sudah ada
        if not db.query(UserTable).filter(UserTable.username == "admin").first():
            admin = UserTable(
                username="admin",
                full_name="Administrator Madin",
                email="hudri366@gmail.com",
                hashed_password=get_password_hash("Madin2026*"), 
                disabled=False
            )
            db.add(admin)
            db.commit()
            print("Akun admin berhasil dibuat di Neon!")
        else:
            print("ℹAdmin sudah ada di database.")
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_admin()