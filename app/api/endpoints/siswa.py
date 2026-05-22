from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import SiswaTable
from app.api.dependencies import get_current_user

# Definisikan Router
router = APIRouter()

# TAMBAH SISWA
@router.post("/add")
async def add_siswa(
    nomor_peserta: str = Form(...),
    nama: str = Form(...),
    kelas: str = Form(...),
    db: Session = Depends(get_db),
    _ = Depends(get_current_user)
):
    # Bersihkan whitespace di awal/akhir input biar data rapi di DB
    nomor_peserta_clean = nomor_peserta.strip()
    nama_clean = nama.strip()
    kelas_clean = kelas.strip()

    # Cek apakah nomor peserta sudah ada
    existing = db.query(SiswaTable).filter(SiswaTable.nomor_peserta == nomor_peserta_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nomor Peserta sudah terdaftar")

    new_siswa = SiswaTable(nomor_peserta=nomor_peserta_clean, nama=nama_clean, kelas=kelas_clean)
    db.add(new_siswa)
    try:
        db.commit()
        return {"status": "success", "message": "Siswa berhasil ditambahkan"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan siswa: {str(e)}")


# UPDATE DATA SISWA
@router.post("/update/{old_nomor_peserta}")
async def update_siswa(
    old_nomor_peserta: str,
    nomor_peserta: str = Form(...), 
    nama: str = Form(...),
    kelas: str = Form(...),
    db: Session = Depends(get_db),
    _ = Depends(get_current_user)
):
    old_no_clean = old_nomor_peserta.strip()
    nomor_peserta_clean = nomor_peserta.strip()
    
    # Cari apakah siswa ada
    query = db.query(SiswaTable).filter(SiswaTable.nomor_peserta == old_no_clean)
    siswa = query.first()
    
    if not siswa:
        raise HTTPException(status_code=404, detail="Siswa tidak ditemukan")
    
    # Jika nomor peserta diubah, cek duplikasi agar tidak bentrok
    if nomor_peserta_clean != old_no_clean:
        existing = db.query(SiswaTable).filter(SiswaTable.nomor_peserta == nomor_peserta_clean).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Nomor {nomor_peserta_clean} sudah digunakan oleh siswa lain")

    # Eksekusi menggunakan .update()
    try:
        query.update({
            SiswaTable.nomor_peserta: nomor_peserta_clean,
            SiswaTable.nama: nama.strip(),
            SiswaTable.kelas: kelas.strip()
        }, synchronize_session='fetch')
        
        db.commit()
        return {"status": "success", "message": "Data berhasil diperbarui"}
    except Exception as e:
        db.rollback()
        print(f"Update Error Detail: {str(e)}")
        raise HTTPException(status_code=400, detail="Gagal memperbarui database. Pastikan format benar.")


# HAPUS SISWA
@router.delete("/delete/{nomor_peserta}")
async def delete_siswa(
    nomor_peserta: str, 
    db: Session = Depends(get_db),
    _ = Depends(get_current_user) # proteksi login agar sinkron dengan fungsi add/update
):
    no_clean = nomor_peserta.strip()
    
    # Cari siswanya
    siswa = db.query(SiswaTable).filter(SiswaTable.nomor_peserta == no_clean).first()

    if not siswa:
        raise HTTPException(status_code=404, detail=f"Siswa dengan nomor {no_clean} tidak ditemukan")

    try:
        db.delete(siswa)
        db.commit()
        return {"status": "success", "message": f"Data {no_clean} berhasil dihapus!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal menghapus: {str(e)}")