from app.database.connection import SessionLocal, engine 
from app.database.models import Base, UserTable 
from app.core.security import get_password_hash # Sesuaikan dengan lokasi security kamu
import os

def create_initial_admin():
    # Pastikan folder data ada di root sebelum membuat database
    if not os.path.exists("data"):
        os.makedirs("data")
        print("Folder 'data' dibuat di root.")

    # Membuat file .db dan tabel users di folder data root
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Cek apakah user admin sudah ada
        if not db.query(UserTable).filter(UserTable.username == "admin").first():
            admin = UserTable(
                username="admin",
                full_name="Administrator Madin",
                email="saepoo334@gmail.com",
                hashed_password=get_password_hash("Madin2026*"), 
                disabled=False
            )
            db.add(admin)
            db.commit()
            print("Akun admin berhasil dibuat!")
        else:
            print("Admin sudah ada di database.")
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_admin()