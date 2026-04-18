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
    # Cari apakah siswa ada
    query = db.query(SiswaTable).filter(SiswaTable.nomor_peserta == old_nomor_peserta)
    siswa = query.first()
    
    if not siswa:
        raise HTTPException(status_code=404, detail="Siswa tidak ditemukan")
    
    # Jika nomor peserta diubah, cek duplikasi
    if nomor_peserta != old_nomor_peserta:
        existing = db.query(SiswaTable).filter(SiswaTable.nomor_peserta == nomor_peserta).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Nomor {nomor_peserta} sudah digunakan")

    # Eksekusi menggunakan .update()
    try:
        query.update({
            SiswaTable.nomor_peserta: nomor_peserta,
            SiswaTable.nama: nama,
            SiswaTable.kelas: kelas
        }, synchronize_session='fetch') # Penting agar session sinkron
        
        db.commit()
        return {"status": "success", "message": "Data berhasil diperbarui"}
    except Exception as e:
        db.rollback()
        print(f"Update Error Detail: {str(e)}")
        raise HTTPException(status_code=400, detail="Gagal memperbarui database. Pastikan format benar.")

# Hapus siswa
@router.delete("/delete/{nomor_peserta}")
async def delete_siswa(
    nomor_peserta: str, 
    db: Session = Depends(get_db), 
    _ = Depends(get_current_user)
    ):
    siswa = db.query(SiswaTable).filter(
        SiswaTable.nomor_peserta == nomor_peserta).first()
    if not siswa:
        raise HTTPException(status_code=404, detail="Siswa tidak ditemukan")
    
    db.delete(siswa)
    db.commit()
    return{"status":"success"}

