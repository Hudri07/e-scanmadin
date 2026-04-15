from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

# Import Internal
from app.database.connection import get_db
from app.api.dependencies import get_current_user
from app.database.models import UserTable, SiswaTable, HasilUjianTable

# Definisikan Router
router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

# --- PUBLIC ROUTES ---

@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Halaman Login"""
    return templates.TemplateResponse("login.html", {"request": request})


# --- PROTECTED ROUTES ---

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(get_current_user)
):
    """Halaman Utama Dashboard"""
    
    # Hitung total siswa
    total_siswa = db.query(SiswaTable).count()

    # Hitung total mapel yang sudah diuji
    ujian_aktif = db.query(HasilUjianTable.mapel).distinct().count()

    # Hitung nilai rata-rata keseluruhan
    rata_rata_nilai = db.query(func.avg(HasilUjianTable.skor)).scalar()
    rata_nilai = round(float(rata_rata_nilai), 1) if rata_rata_nilai else 0

    # Aktivitas terbaru
    aktivitas_terbaru = db.query(HasilUjianTable, SiswaTable)\
        .join(SiswaTable, HasilUjianTable.nomor_peserta == SiswaTable.nomor_peserta)\
        .order_by(HasilUjianTable.id.desc())\
        .limit(5).all()
    
    # Data untuk Grafik: Rata-rata nilai per kelas
    grafik_data = db.query(
        SiswaTable.kelas, 
        func.avg(HasilUjianTable.skor).label('rata_rata')
    ).join(HasilUjianTable, SiswaTable.nomor_peserta == HasilUjianTable.nomor_peserta)\
    .group_by(SiswaTable.kelas).all()

    # Format untuk Chart.js (Label dan Data)
    labels_grafik = [d[0] for d in grafik_data]
    values_grafik = [round(float(d[1]), 1) for d in grafik_data]
    
    return templates.TemplateResponse("dashboard.html",{
        "request": request,
        "user": current_user,
        "total_siswa": total_siswa,
        "ujian_aktif": ujian_aktif,
        "rata_nilai": rata_nilai,
        "aktivitas": aktivitas_terbaru,
        "labels_grafik": labels_grafik,
        "values_grafik": values_grafik,
        "perlu_koreksi": 0
    })

@router.get("/koreksi", response_class=HTMLResponse)
async def koreksi_page(
    request: Request, 
    current_user: UserTable = Depends(get_current_user)
):
    """Halaman Proses Scan LJK"""
    return templates.TemplateResponse("koreksi.html", {
        "request": request, 
        "user": current_user
    })


@router.get("/manajemen-kelas", response_class=HTMLResponse)
async def manajemen_kelas(
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: UserTable = Depends(get_current_user)
):
    """Halaman Pengaturan Data Siswa"""
    # Ambil semua data siswa dari database
    semua_siswa = db.query(SiswaTable).all()

    kelas_list = db.query(SiswaTable.kelas).distinct().all()
    kelas_list = [k[0] for k in kelas_list if k[0]]

   # Susun data siswa beserta seluruh nilai mapelnya
    siswa_data = []
    for s in semua_siswa:
        # Cari Semua hasil ujian untuk nomor peserta ini
        daftar_hasil = db.query(HasilUjianTable).filter(
            HasilUjianTable.nomor_peserta == s.nomor_peserta
        ).all()
        
        # Format menjadi list of dict agar mudah di-loop di JavaScript
        nilai_lengkap = [
            {"mapel": h.mapel, "skor": h.skor} for h in daftar_hasil
        ]
        
        siswa_data.append({
            "nomor_peserta": s.nomor_peserta,
            "nama": s.nama,
            "kelas": s.kelas,
            "nilai_lengkap": nilai_lengkap
        })
    
    return templates.TemplateResponse("kelas.html", {
        "request": request, 
        "user": current_user,
        "siswa": siswa_data,
        "kelas_list": kelas_list
    })

# Menampilkan Halaman Profile
@router.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request, user: UserTable = Depends(get_current_user)):
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": user
    })