from fastapi import APIRouter, Request, Depends, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timedelta

# Import Internal
from app.database.connection import get_db
from app.core.templates import templates
from app.api.dependencies import get_current_user
from app.database.models import UserTable, SiswaTable, HasilUjianTable

# Definisikan Router
router = APIRouter()

# --- PUBLIC ROUTES ---

@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Halaman Login"""
    return templates.TemplateResponse(
        request=request,
        name="login.html"
        )


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
    
    return templates.TemplateResponse(
        request= request,
        name="dashboard.html",
        context={
            "user": current_user,
            "total_siswa": total_siswa,
            "ujian_aktif": ujian_aktif,
            "rata_nilai": rata_nilai,
            "aktivitas": aktivitas_terbaru,
            "labels_grafik": labels_grafik,
            "values_grafik": values_grafik
            }
        )

@router.get("/koreksi", response_class=HTMLResponse)
async def koreksi_page(
    request: Request, 
    current_user: UserTable = Depends(get_current_user)
):
    """Halaman Proses Scan LJK"""
    return templates.TemplateResponse(
        request= request, 
        name="koreksi.html", 
        context={
            "user": current_user
            }
        )


@router.get("/manajemen-kelas", response_class=HTMLResponse)
async def manajemen_kelas(
    request: Request, 
    page: int = Query(1, ge=1),
    search: str = Query(None),
    kelas: str = Query(None),
    db: Session = Depends(get_db), 
    current_user: UserTable = Depends(get_current_user)
):
    # 1. Base query
    query = db.query(SiswaTable)
    
    # 2. Filter kelas
    if kelas:
        query = query.filter(SiswaTable.kelas == kelas)
        
    # 3. Filter pencarian
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                SiswaTable.nama.ilike(search_filter),
                SiswaTable.nomor_peserta.ilike(search_filter)
            )
        )
    
    # 4. Pagination (Limit 10 per halaman)
    limit = 10
    total_siswa = query.count()
    total_pages = (total_siswa + limit - 1) // limit if total_siswa > 0 else 1
    offset = (page - 1) * limit
    
    # 5. Eksekusi data
    data_siswa_raw = query.offset(offset).limit(limit).all()
    
    # 6. Susun data dengan nilai
    siswa_data = []
    for s in data_siswa_raw:
        daftar_hasil = db.query(HasilUjianTable).filter(
            HasilUjianTable.nomor_peserta == s.nomor_peserta
        ).all()
        siswa_data.append({
            "nomor_peserta": s.nomor_peserta,
            "nama": s.nama,
            "kelas": s.kelas,
            "nilai_lengkap": [{"mapel": h.mapel, "skor": h.skor} for h in daftar_hasil]
        })
    
    # 7. Ambil daftar kelas untuk menu (tetap ambil semua untuk dropdown)
    kelas_list = [k[0] for k in db.query(SiswaTable.kelas).distinct().all() if k[0]]

    return templates.TemplateResponse(
        request= request,
        name="kelas.html", 
        context= {
            "request": request,
            "user": current_user,
            "siswa": siswa_data,
            "kelas_list": kelas_list,
            "current_page": page,
            "total_pages": total_pages,
            "search": search,
            "active_kelas": kelas
        }
    )


# Menampilkan Halaman Profile
@router.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request, user: UserTable = Depends(get_current_user)):
    return templates.TemplateResponse(
        request= request, 
        name="profile.html",
        context= {
            "user": user
            }
    )