import cv2
import os
import io
import shutil
import json
import uuid
import time
import pytz
import asyncio

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
    # 1. Ambil kunci jawaban di awal
    kunci_db = db.query(models.KunciJawabanTable).filter(
        models.KunciJawabanTable.mapel == mapel_aktif
    ).order_by(models.KunciJawabanTable.id.desc()).first()
    
    if not kunci_db:
        raise HTTPException(status_code=400, detail="Kunci jawaban tidak ditemukan!")

    kunci_jawaban = json.loads(kunci_db.kunci_json) if isinstance(kunci_db.kunci_json, str) else kunci_db.kunci_json
    
    # Helper function untuk memproses satu file di dalam memori (Irit RAM Server Gratisan)
    async def proses_single_file(file: UploadFile):
        try:
            # ⚡ OPTIMASI UTAMA: Baca file langsung ke RAM Bytes, tidak perlu tulis ke data/uploads/
            file_bytes = await file.read()

            # Jalankan OMR Service menggunakan Thread Pool agar FastAPI tidak macet (Non-blocking)
            # Mengirim data bytes ke fungsi omr_service yang baru
            hasil_omr = await asyncio.to_thread(scan_jawaban, file_bytes)
            
            if not hasil_omr:
                return {"nama": file.filename, "message": "Gagal memproses gambar LJK", "status": "error"}

            # Ambil data dari kembalian OMR Service terbaru
            nama_siswa = hasil_omr.get("nama", "Tanpa Nama")
            nomor_omr = hasil_omr.get("nomor", "000")
            jawaban_siswa = hasil_omr.get("jawaban", [])
            gambar_bukti_b64 = hasil_omr.get("gambar_bukti", "") # 💎 Base64 String baru untuk Frontend

            # Jika nama_siswa kosong atau hanya spasi, beri fallback nama file
            if not nama_siswa.strip():
                nama_siswa = "Tanpa Nama / Tidak Terbaca"

            # Gabungkan format nomor peserta dengan validasi tanda hubung ganda
            nomor_omr_clean = nomor_omr.replace("-", "0") if "-" in nomor_omr else nomor_omr
            nomor_peserta = f"26-06-0056-1-{nomor_omr_clean}"

            # --- CEK DUPLIKAT NILAI ---
            exists = db.query(models.HasilUjianTable).filter(
                and_(
                    models.HasilUjianTable.nomor_peserta == nomor_peserta,
                    models.HasilUjianTable.mapel == mapel_aktif
                )
            ).first()

            if exists:
                # Ambil skor dari database saja jika duplikat, jangan hitung ulang
                detail_benar = 0
                detail_salah = 0
                perbandingan = []
                
                if jawaban_siswa:
                    _, detail_benar, detail_salah, perbandingan = hitung_skor(jawaban_siswa, kunci_jawaban)
                
                return {
                    "nama": nama_siswa,  
                    "nomor_peserta": nomor_peserta,
                    "is_duplicate": True, 
                    "skor": exists.skor,  
                    "detail": {"benar": detail_benar, "salah": detail_salah},
                    "perbandingan": perbandingan,
                    "telegram_message_id": exists.telegram_message_id,
                    "gambar_bukti": gambar_bukti_b64, # Tetap sertakan gambar ke frontend meskipun duplikat
                    "message": "Siswa ini sudah dikoreksi sebelumnya."
                }

            # --- PROSES INTEGRASI TELEGRAM ---
            caption = (f" Koreksi Berhasil\n\n"
                      f" Siswa: {nama_siswa}\n"
                      f" Nomor: {nomor_peserta}\n"
                      f" Mapel: {mapel_aktif}\n")
            
            # Jika Anda ingin mengirim gambar asli yang polos ke Telegram: gunakan `file_bytes`
            # Namun, jika nanti Anda ingin mengirim gambar hasil lingkaran ke Telegram, Anda harus mengonversi kembali string base64 ke bytes di sini. Kita pakai `file_bytes` asli dulu agar aman.
            tele_msg_id = await send_to_telegram(file_bytes, file.filename, caption)

            # --- PROSES HITUNG SKOR ---
            if jawaban_siswa and len(jawaban_siswa) > 0:
                skor, benar, salah, perbandingan = hitung_skor(jawaban_siswa, kunci_jawaban)
                return {
                    "nama": nama_siswa,
                    "nomor_peserta": nomor_peserta,
                    "skor": skor,
                    "is_duplicate": False,
                    "detail": {"benar": benar, "salah": salah}, 
                    "perbandingan": perbandingan, 
                    "telegram_message_id": tele_msg_id,
                    "gambar_bukti": gambar_bukti_b64 # 💎 Dikirim balik ke JavaScript Frontend Anda
                }
            else:
                return {
                    "nama": file.filename, 
                    "message": "Gagal mendeteksi jawaban pada lembar LJK",
                    "status": "error"
                }
                
        except Exception as e:
            print(f"❌ ERROR memproses {file.filename}: {e}")
            return {
                "nama": file.filename, 
                "message": f"Gagal proses: {str(e)}",
                "status": "error"
            }

    # Memproses banyak file secara paralel/simultan memanfaatkan resource server gratisan secara optimal
    tasks = [proses_single_file(file) for file in files]
    hasil_bulk = await asyncio.gather(*tasks)
            
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