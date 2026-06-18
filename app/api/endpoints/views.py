from fastapi import APIRouter, Request, Depends, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timedelta
import pytz

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
        name="login.html",
        context={
            "user": None
            }
        )


# --- PROTECTED ROUTES ---

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(get_current_user)
):
    """Halaman Utama Dashboard"""
    
    # Definisikan timezone WIB (Asia/Jakarta)
    tz_jakarta = pytz.timezone('Asia/Jakarta')
    hari_ini = datetime.now(tz_jakarta) # Jam sekarang otomatis berbasis WIB

    # Hitung total siswa
    total_siswa = db.query(SiswaTable).count()

    # Hitung total mapel yang sudah diuji
    ujian_aktif = db.query(HasilUjianTable.mapel).distinct().count()

    # Hitung nilai rata-rata keseluruhan
    rata_rata_nilai = db.query(func.avg(HasilUjianTable.skor)).scalar()
    rata_nilai = round(float(rata_rata_nilai), 1) if rata_rata_nilai else 0

    # Aktivitas terbaru
    aktivitas_raw = db.query(HasilUjianTable, SiswaTable)\
        .join(SiswaTable, HasilUjianTable.nomor_peserta == SiswaTable.nomor_peserta)\
        .order_by(HasilUjianTable.id.desc())\
        .limit(5).all()
    
    aktivitas_terbaru = []
    for hasil, siswa in aktivitas_raw:
        tanggal_db = hasil.tanggal 
        
        if tanggal_db:
            # Jika dari DB tipenya datetime tapi masih naive (tanpa tz), tempelkan tz Jakarta
            if isinstance(tanggal_db, datetime):
                if tanggal_db.tzinfo is None:
                    # Jika di DB disimpan sebagai UTC, konversi ke Jakarta:
                    tanggal_wib = pytz.utc.localize(tanggal_db).astimezone(tz_jakarta)
                    # Jika di DB emang waktu lokal tapi ga ada flag-nya, gunakan localize:
                    tanggal_wib = tz_jakarta.localize(tanggal_db)
                else:
                    tanggal_wib = tanggal_db.astimezone(tz_jakarta)
                
                tanggal_str = tanggal_wib.strftime('%d %b %H:%M')
            else:
                # Jika tipe data string mentah
                tanggal_str = str(tanggal_db)[:16]
        else:
            tanggal_str = "Baru"

        aktivitas_terbaru.append((
            {
                "skor": hasil.skor,
                "mapel": hasil.mapel,
                "created_at": tanggal_str
            },
            siswa
        ))
    
    # Grafik Tren Koreksi LJK 7 Hari Terakhir
    daftar_hari = [hari_ini - timedelta(days=i) for i in range(6, -1, -1)]
    
    labels_grafik = []
    values_grafik = []
    
    for hari in daftar_hari:
        labels_grafik.append(hari.strftime('%d %b'))
        
        # Batasan jam harian timezone Jakarta
        start_date = datetime(hari.year, hari.month, hari.day, 0, 0, 0, tzinfo=tz_jakarta)
        end_date = datetime(hari.year, hari.month, hari.day, 23, 59, 59, tzinfo=tz_jakarta)
        
        jumlah_koreksi_harian = db.query(HasilUjianTable).filter(
            HasilUjianTable.tanggal >= start_date,
            HasilUjianTable.tanggal <= end_date
        ).count()
            
        values_grafik.append(jumlah_koreksi_harian)
    
    return templates.TemplateResponse(
        request=request,
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

@router.get("/manajemen-siswa", response_class=HTMLResponse)
async def manajemen_siswas(
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
    
    # 4. Eksekusi data
    data_siswa_raw = db.query(SiswaTable).all()
    
    # 5. Susun data dengan nilai
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
        name="siswa.html", 
        context= {
            "request": request,
            "user": current_user,
            "siswa": siswa_data,
            "kelas_list": kelas_list,
            "current_page": page,
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

@router.get("/manajemen-kunci", response_class=HTMLResponse)
async def manajemen_kunci_page(
    request: Request, 
    current_user: UserTable = Depends(get_current_user)
):
    """Halaman Master Data Kunci Jawaban"""
    return templates.TemplateResponse(
        request=request, 
        name="manajemen_kunci.html",
        context={
            "user": current_user
        }
    )

@router.get("/riwayat-ujian", response_class=HTMLResponse)
async def riwayat_ujian_page(
    request: Request,
    current_user: UserTable = Depends(get_current_user)
):
    """Merender halaman HTML utama untuk Riwayat Ujian"""
    return templates.TemplateResponse(
        request=request,
        name="riwayat_ujian.html",
        context={"user": current_user}
    )

@router.get("/api/riwayat-ujian")
async def get_api_riwayat_ujian(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(get_current_user)
):
    """Menyuplai data JSON"""
    riwayat_raw = db.query(HasilUjianTable, SiswaTable).join(
        SiswaTable, HasilUjianTable.nomor_peserta == SiswaTable.nomor_peserta
    ).order_by(HasilUjianTable.id.desc()).all()
    
    tz_jakarta = pytz.timezone('Asia/Jakarta')
    daftar_riwayat = []
    
    for hasil, siswa in riwayat_raw:
        tanggal_db = hasil.tanggal
        if tanggal_db and isinstance(tanggal_db, datetime):
            if tanggal_db.tzinfo is None:
                tanggal_wib = tz_jakarta.localize(tanggal_db)
            else:
                tanggal_wib = tanggal_db.astimezone(tz_jakarta)
            tanggal_str = tanggal_wib.strftime('%d %b %Y - %H:%M')
        else:
            tanggal_str = str(tanggal_db)[:16] if tanggal_db else "-"

        daftar_riwayat.append({
            "id_hasil": hasil.id,
            "nomor_peserta": hasil.nomor_peserta,
            "nama": siswa.nama,
            "kelas": siswa.kelas,
            "mapel": hasil.mapel,
            "skor": hasil.skor,
            "tanggal": tanggal_str
        })
        
    return {"sukses": True, "riwayat": daftar_riwayat}