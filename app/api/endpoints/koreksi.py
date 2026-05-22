import cv2
import os
import io
import shutil
import json
import uuid
import time
import pytz

from datetime import datetime
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

@router.get("/get-kunci/{kunci_id}")
async def get_single_kunci(kunci_id: int, db: Session = Depends(get_db)):
    """Mengambil satu kunci jawaban spesifik untuk auto-fill form edit di Koreksi LJK"""
    kunci = db.query(models.KunciJawabanTable).filter(models.KunciJawabanTable.id == kunci_id).first()
    if not kunci:
        raise HTTPException(status_code=404, detail="Kunci jawaban tidak ditemukan")
        
    return {
        "id": kunci.id,
        "mapel": kunci.mapel,
        "kelas": kunci.kelas,
        "kunci": json.loads(kunci.kunci_json) if isinstance(kunci.kunci_json, str) else kunci.kunci_json
    }

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
            time.sleep(0.1)

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
                # Walaupun duplikat, kita tetap hitung skor dari hasil OMR saat ini 
                if jawaban_siswa:
                    skor_omr, benar, salah, perbandingan = hitung_skor(jawaban_siswa, kunci_jawaban)
                else:
                    benar, salah, perbandingan = 0, 0, []

                hasil_bulk.append({
                    "nama": nama_siswa,
                    "nomor_peserta": nomor_peserta,
                    "is_duplicate": True, 
                    "skor": exists.skor, 
                    "detail": {"benar": benar, "salah": salah},
                    "perbandingan": perbandingan,
                    "telegram_message_id": exists.telegram_message_id,
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
        # Siapkan Waktu WIB Jakarta
        tz_jakarta = pytz.timezone('Asia/Jakarta')
        waktu_sekarang_wib = datetime.now(tz_jakarta)

        # Ambil info kelas dari Kunci Jawaban berdasarkan Mapel
        kunci_info = db.query(models.KunciJawabanTable).filter_by(mapel=payload.mapel).first()
        kelas_asli = kunci_info.kelas if kunci_info else "Tidak Diketahui"
        
        # List sementara untuk menampung data telegram yang perlu di-update setelah DB sukses
        telegram_updates = []

        # ITERASI UTAMA: FOKUS SIMPAN KE DATABASE DULU (ANTI MACET)
        for s in payload.siswa:
            # Cari atau daftarkan siswa baru
            siswa = db.query(models.SiswaTable).filter_by(nomor_peserta=s.nomor_peserta_baru).first()
            if not siswa:
                siswa = models.SiswaTable(
                    nomor_peserta=s.nomor_peserta_baru, 
                    nama=s.nama,
                    kelas=kelas_asli
                )
                db.add(siswa)
                db.flush()

            # Pastikan konversi ID Telegram aman
            tele_id = None
            if s.telegram_message_id is not None:
                try:
                    # Amankan konversi ke integer murni
                    nama_id_str = str(s.telegram_message_id).strip()
                    if nama_id_str.replace('.', '', 1).isdigit() or nama_id_str.isdigit():
                        val_int = int(float(nama_id_str))
                        if val_int > 0:
                            tele_id = val_int
                except ValueError:
                    tele_id = None

            # Cari data nilai yang sudah ada
            hasil = db.query(models.HasilUjianTable).filter(
                and_(
                    models.HasilUjianTable.nomor_peserta == s.nomor_peserta_baru,
                    models.HasilUjianTable.mapel == payload.mapel
                )
            ).first()

            if hasil:
                hasil.skor = s.skor
                hasil.tanggal = waktu_sekarang_wib 
                if tele_id:
                    hasil.telegram_message_id = tele_id
            else:
                hasil = models.HasilUjianTable(
                    nomor_peserta=s.nomor_peserta_baru,
                    mapel=payload.mapel,
                    skor=s.skor,
                    tanggal=waktu_sekarang_wib,
                    telegram_message_id=tele_id
                )
                db.add(hasil)
            
            # Jika ada ID Telegram valid, masukkan ke antrean update nanti
            if tele_id:
                telegram_updates.append({
                    "tele_id": tele_id,
                    "nama": s.nama,
                    "nomor": s.nomor_peserta_baru,
                    "skor": s.skor
                })

        # COMMIT KE DATABASE TERLEBIH DAHULU!
        db.commit()
        print("✅ DATA BERHASIL DI-COMMIT KE DATABASE NEON!")

        # PROSES UPDATE TELEGRAM DI AKHIR (JIKA ADA EROR TIDAK AKAN MERUSAK DB)
        for t in telegram_updates:
            caption_final = (
                f" **HASIL UJIAN TERVERIFIKASI** \n\n"
                f" Nama: {t['nama']}\n"
                f" Nomor Peserta: {t['nomor']}\n"
                f" Mata Pelajaran: {payload.mapel}\n"
                f" **Skor Akhir: {t['skor']}**"
            )
            try:
                # Panggil update caption Telegram
                await edit_telegram_caption(t["tele_id"], caption_final)
                print(f"🔹 Telegram Caption Berhasil Diupdate untuk ID: {t['tele_id']}")
            except Exception as tele_err:
                # Log eror telegram, tapi abaikan agar response backend ke frontend tetap jalan lancar!
                print(f"Gagal update caption Telegram ID {t['tele_id']} tapi DB aman: {tele_err}")

        # Kembalikan response sukses ke JavaScript frontend
        return {"status": "success", "message": "Data berhasil disimpan ke database!"}
        
    except Exception as e:
        db.rollback()
        print(f"DATABASE ROLLBACK AKIBAT EROR UTAMA: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan data: {str(e)}")