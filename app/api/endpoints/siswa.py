from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import SiswaTable
from app.api.dependencies import get_current_user

# Definisikan Router
router = APIRouter()

# Tambah siswa
@router.post("/add")
async def add_siswa(
    nomor_peserta: str = Form(...),
    nama: str = Form(...),
    kelas: str = Form(...),
    db:Session = Depends(get_db),
    _ = Depends(get_current_user)
):
    # Cek apakah nomor peserta sudah ada
    existing = db.query(SiswaTable).filter(SiswaTable.nomor_peserta == nomor_peserta).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nomor Peserta sudah terdaftar")

    new_siswa = SiswaTable(nomor_peserta=nomor_peserta, nama=nama, kelas=kelas)
    db.add(new_siswa)
    db.commit()
    return{"status": "success", "message": "Siswa berhasil ditambahkan"}

# Update data siswa
@router.post("/update/{old_nomor_peserta}")
async def update_siswa(
    old_nomor_peserta: str,
    nomor_peserta: str = Form(...), 
    nama: str = Form(...),
    kelas: str = Form(...),
    db: Session = Depends(get_db),
    _ = Depends(get_current_user)
):
    # Cari data siswa yang mau diedit
    siswa = db.query(SiswaTable).filter(SiswaTable.nomor_peserta == old_nomor_peserta).first()
    if not siswa:
        raise HTTPException(status_code=404, detail="Siswa tidak ditemukan")
    
    # Jika nomor peserta diubah, cek apakah nomor baru sudah ada yang punya
    if nomor_peserta != old_nomor_peserta:
        existing = db.query(SiswaTable).filter(SiswaTable.nomor_peserta == nomor_peserta).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Nomor {nomor_peserta} sudah digunakan siswa lain")

    # Eksekusi perubahan
    try:
        siswa.nomor_peserta = nomor_peserta
        siswa.nama = nama
        siswa.kelas = kelas
        db.commit()
        return {"status": "success", "message": "Data berhasil diperbarui"}
    except Exception as e:
        db.rollback()
        # Cetak error ke terminal uvicorn untuk debug lebih lanjut
        print(f"Update Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Gagal memperbarui data database")

# Hapus siswa
@router.delete("/delete/{nomor_peserta}")
async def delete_siswa(nomor_peserta: str, db: Session = Depends(get_db), _ = Depends(get_current_user)):
    siswa = db.query(SiswaTable).filter(SiswaTable.nomor_peserta == nomor_peserta).first()
    if not siswa:
        raise HTTPException(status_code=404, detail="Siswa tidak ditemukan")
    
    db.delete(siswa)
    db.commit()
    return{"status":"success"}