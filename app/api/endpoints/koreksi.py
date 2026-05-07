import cv2
import os
import io
import shutil
import json
import uuid
import time

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Import Service & Database 
from app.services.ocr_service import preprocessing
from app.services.llm_service import get_data_from_gemini, get_identitas_siswa
from app.services.omr_service import scan_jawaban
from app.services.scorer_service import hitung_skor
from app.services.telegram_service import send_to_telegram, edit_telegram_caption
from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.database import models
from app.schemas.hasil import PayloadSimpanHasil

# Definisikan Router
router = APIRouter()

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/list-kunci")
async def get_list_kunci(db: Session = Depends(get_db)):
    """Mengambil daftar kunci jawaban untuk dropdown di frontend"""
    keys = db.query(models.KunciJawabanTable).all()
    return [
        {
            "id": k.id, 
            "mapel": k.mapel, 
            "kelas": k.kelas, 
            # Cek tipe data sebelum json.loads
            "kunci": json.loads(k.kunci_json) if isinstance(k.kunci_json, str) else k.kunci_json
        } for k in keys
    ]

@router.post("/proses-kunci")
async def proses_kunci(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Buat nama file unik dengan UUID
    unique_id = uuid.uuid4().hex[:6]
    file_path = os.path.join(UPLOAD_DIR, f"kunci_{unique_id}.jpg")
    cleaned_path = None

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Simpan path hasil preprocessing
    cleaned_path = preprocessing(file_path)
    
    try:
        raw_json = get_data_from_gemini(cleaned_path)
        data = json.loads(raw_json)
        mapel = data.get("mata_pelajaran", "Ujian Madin")
        kelas = data.get("kelas", "-")
        jawaban = data.get("jawaban", [])
        
        # CEK DUPLIKAT
        existing_kunci = db.query(models.KunciJawabanTable).filter(
            models.KunciJawabanTable.mapel == mapel,
            models.KunciJawabanTable.kelas == kelas
        ).first()

        if existing_kunci:
            # Update kunci yang sudah ada
            existing_kunci.kunci_json = json.dumps(jawaban)
            kunci_final = existing_kunci
        else:
            # Buat baru jika belum ada
            kunci_final = models.KunciJawabanTable(
                mapel=mapel,
                kelas=kelas,
                kunci_json=json.dumps(jawaban)
            )
            db.add(kunci_final)
        
        db.commit()
        db.refresh(kunci_final)
        
        return {
            "status": "success", 
            "id": kunci_final.id,
            "mata_pelajaran": kunci_final.mapel,
            "kelas": kunci_final.kelas,
            "data": jawaban
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Hapus file asli
        if os.path.exists(file_path):
            os.remove(file_path)

        # Hapus file hasil preprocessing
        if cleaned_path and os.path.exists(cleaned_path):
            os.remove(cleaned_path)

@router.post("/scan-bulk")
async def scan_bulk(
    files: list[UploadFile] = File(...), 
    mapel_aktif: str = Form(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Ambil kunci terbaru berdasarkan mapel yang sedang aktif
    kunci_db = db.query(models.KunciJawabanTable).filter(
        models.KunciJawabanTable.mapel == mapel_aktif
    ).order_by(models.KunciJawabanTable.id.desc()).first()
    
    if not kunci_db:
        raise HTTPException(status_code=400, detail="Kunci jawaban tidak ditemukan!")

    kelas_asli = kunci_db.kelas

    # Jika data sudah list, jangan di-json.loads lagi
    if isinstance(kunci_db.kunci_json, str):
        kunci_jawaban = json.loads(kunci_db.kunci_json)
    else:
        kunci_jawaban = kunci_db.kunci_json

    hasil_bulk = []
    
    for file in files:
        file_content = await file.read()
        file_path = os.path.join(UPLOAD_DIR, f"temp_{uuid.uuid4().hex}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

        try:
            # Berikan sedikit jeda agar proses file sistem stabil
            time.sleep(0.2)

            # Jalankan OMR
            hasil_omr = scan_jawaban(file_path)
            jawaban_siswa = hasil_omr["jawaban"]
            nomor_omr = hasil_omr["nomor"]

            # Kirim Ke LLM GEMINI 
            identitas = get_identitas_siswa(file_path) 
            nama_siswa = identitas.get("nama", "Tanpa Nama")
            
            # Gabungkan format nomor peserta
            nomor_peserta = f"26-06-0056-1-{nomor_omr}"

            # --- CEK DUPLIKAT NILAI ---
            exists = db.query(models.HasilUjianTable).filter(
                and_(
                    models.HasilUjianTable.nomor_peserta == nomor_peserta,
                    models.HasilUjianTable.mapel == mapel_aktif
                )
            ).first()

            if exists:
                hasil_bulk.append({
                    "nama": nama_siswa,
                    "nomor_peserta": nomor_peserta,
                    "is_duplicate": True,
                    "skor": exists.skor,
                    "message": "Siswa ini sudah dikoreksi sebelumnya."
                })
                continue

            # INTEGRASI TELEGRAM
            caption = (f" Koreksi Berhasil\n\n"
                       f" Siswa: {nama_siswa}\n"
                       f" Nomor: {nomor_peserta}\n"
                       f" Mapel: {mapel_aktif}\n"
            )
            
            tele_msg_id = await send_to_telegram(file_content, file.filename, caption)

            # --- PROSES SKOR ---
            if jawaban_siswa:
                skor, benar, salah, perbandingan = hitung_skor(jawaban_siswa, kunci_jawaban)

                hasil_bulk.append({
                    "nama": nama_siswa,
                    "nomor_peserta": nomor_peserta,
                    "skor": skor,
                    "is_duplicate": False,
                    "detail": {"benar": benar, "salah": salah}, 
                    "perbandingan": perbandingan, 
                    "telegram_message_id": tele_msg_id
                })
            else:
                hasil_bulk.append({
                    "nama": file.filename, 
                    "message": "Gagal mendeteksi jawaban pada lembar LJK",
                    "status": "error"
                })
                
        except Exception as e:
            print(f"ERROR processing {file.filename}: {e}")
            db.rollback()
            hasil_bulk.append({
                "nama": file.filename, 
                "message": f"Gagal proses: {str(e)}",
                "status": "error"
                })
            
        finally:
            # Selalu hapus file temporary setelah diproses
            if os.path.exists(file_path): 
                os.remove(file_path)
            
    return {"status": "success", "data": hasil_bulk}

@router.post("/simpan-hasil")
async def simpan_hasil_manual(payload: PayloadSimpanHasil, db: Session = Depends(get_db)):
    try:
        # Ambil info kelas dari Kunci Jawaban berdasarkan Mapel
        kunci_info = db.query(models.KunciJawabanTable).filter_by(mapel=payload.mapel).first()
        kelas_asli = kunci_info.kelas if kunci_info else "Tidak Diketahui"
        
        for s in payload.siswa:
            # 1. Logic Pencarian/Pendaftaran Siswa
            siswa = db.query(models.SiswaTable).filter_by(nomor_peserta=s.nomor_peserta_baru).first()
            if not siswa:
                siswa = models.SiswaTable(
                    nomor_peserta=s.nomor_peserta_baru, 
                    nama=s.nama,
                    kelas=kelas_asli
                )
                db.add(siswa)
                db.flush()

            # 2. Update atau Insert Nilai
            hasil = db.query(models.HasilUjianTable).filter(
                and_(
                    models.HasilUjianTable.nomor_peserta == s.nomor_peserta_baru,
                    models.HasilUjianTable.mapel == payload.mapel
                )
            ).first()

            if hasil:
                hasil.skor = s.skor
                hasil.telegram_message_id = s.telegram_message_id
            else:
                hasil = models.HasilUjianTable(
                    nomor_peserta=s.nomor_peserta_baru,
                    mapel=payload.mapel,
                    skor=s.skor
                )
                db.add(hasil)
            
            # KIRIM KE TELEGRAM 
            caption_final = (
                f" **HASIL UJIAN TERVERIFIKASI**\n\n"
                f" Nama: {s.nama}\n"
                f" Nomor Peserta: {s.nomor_peserta_baru}\n"
                f" Mata Pelajaran: {payload.mapel}\n"
                f" **Skor Akhir: {s.skor}**"
            )
            await edit_telegram_caption(s.telegram_message_id, caption_final)
        
        db.commit()
        return {"status": "success", "message": "Data berhasil diperbarui dan dikirim ke Telegram"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))