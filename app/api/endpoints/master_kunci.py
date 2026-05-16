from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database import models
import json

router = APIRouter()

@router.delete("/hapus/{id}")
async def hapus_kunci(id: int, db: Session = Depends(get_db)):
    kunci = db.query(models.KunciJawabanTable).filter(models.KunciJawabanTable.id == id).first()
    if not kunci:
        raise HTTPException(status_code=404, detail="Data tidak ditemukan")
    
    db.delete(kunci)
    db.commit()
    return {"status": "success", "message": "Kunci berhasil dihapus"}

@router.post("/update-kunci-manual")
async def update_kunci_manual(
    id_kunci: int = Form(...), 
    mapel: str = Form(...),   
    kelas: str = Form(...),   
    jawaban: str = Form(...), 
    db: Session = Depends(get_db)
):
    kunci_entry = db.query(models.KunciJawabanTable).filter(models.KunciJawabanTable.id == id_kunci).first()
    
    if not kunci_entry:
        raise HTTPException(status_code=404, detail="Data kunci tidak ditemukan")

    try:
        # Update semua field yang mungkin diubah user di UI
        kunci_entry.mapel = mapel
        kunci_entry.kelas = kelas
        kunci_entry.kunci_json = jawaban 
        
        db.commit()
        return {"status": "success", "message": "Data kunci berhasil diperbarui!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
