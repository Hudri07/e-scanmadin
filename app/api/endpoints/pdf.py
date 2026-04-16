from fpdf import FPDF
from fastapi import APIRouter, Response
from hijri_converter import Gregorian
from datetime import datetime
import io

# Definisikan router
router = APIRouter()

# Konversi angka ke huruf
def terbilang_nilai(n):
    n = int(n)
    kata = ["Nol", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
    if n < 12:
        return kata[n]
    elif n < 20:
        return kata[n % 10] + " Belas"
    elif n < 100:
        return kata[n // 10] + " Puluh " + (kata[n % 10] if n % 10 != 0 else "")
    elif n == 100:
        return "Seratus"
    return str(n)

# Ambil Fungsi Tanggal Hijriyah
def get_tgl_hijriyah():
    # Mengambil tanggal hari ini (M) dan konversi ke H
    today = Gregorian.today()
    h = today.to_hijri()
    # Daftar nama bulan H
    bulan_hijri = [
        "Muharram", "Safar", "Rabi'ul Awwal", "Rabi'ul Akhir",
        "Jumadil Awwal", "Jumadil Akhira", "Rajab", "Sya'ban",
        "Ramadhan", "Syawwal", "Dzulqa'dah", "Dzulhijjah"
    ]
    return f"{h.day} {bulan_hijri[h.month - 1]} {h.year} H"

@router.post("/ekspor-pdf")
async def ekspor_pdf(data: dict):
    # Setup PDF
    pdf = FPDF('P', 'mm', 'A4')
    pdf.add_page()

    # 1. Ambil data tahun dari request
    th_h_sekarang = int(data.get('tahun_hijriyah', 1447))
    th_m_sekarang = int(data.get('tahun_masehi', 2026))

    # 2. Hitung tahun sebelumnya
    th_h_sebelum = th_h_sekarang - 1
    th_m_sebelum = th_m_sekarang - 1

    # 3. Format ke dalam string rentang
    tahun_hijri_str = f"{th_h_sebelum}-{th_h_sekarang} H"
    tahun_masehi_str = f"{th_m_sebelum}-{th_m_sekarang} M"
    
    # --- 1. HEADER TENGAH ---
    pdf.set_font("Times", "B", 14)
    pdf.cell(0, 8, "DAFTAR NILAI AKHIR BERSAMA", ln=True, align="C")
    pdf.cell(0, 8, "MADRASAH DINIYAH TAKMILIYAH AWALIYAH", ln=True, align="C")
    pdf.set_font("Times", "", 12)
    pdf.cell(0, 8, f"TAHUN PEMBELAJARAN {tahun_hijri_str} / {tahun_masehi_str}", ln=True, align="C")
    pdf.ln(10)

    # --- 2. IDENTITAS SISWA ---
    pdf.set_font("Times", "", 11)
    pdf.cell(30, 7, "Nama", border=0)
    pdf.cell(0, 7, f": {data['nama']}", ln=True)
    pdf.cell(30, 7, "No. Ujian", border=0)
    pdf.cell(0, 7, f": {data['nomor_peserta']}", ln=True)
    pdf.ln(5)

    # --- 3. TABEL NILAI ---
    # Header Tabel
    pdf.set_font("Times", "B", 11)
    pdf.cell(10, 10, "No", border=1, align="C")
    pdf.cell(100, 10, "Bidang Studi", border=1, align="C")
    pdf.cell(80, 5, "Nilai", border=1, ln=1, align="C") # Baris atas nilai
    pdf.cell(110) # Geser posisi ke kolom Nilai
    pdf.cell(40, 5, "Angka", border=1, align="C")
    pdf.cell(40, 5, "Huruf", border=1, ln=1, align="C")

    # Data Tabel 
    list_nilai = data.get('list_nilai',[])
    if not list_nilai:
        list_nilai = [{
            "mapel": data.get('mapel', '-'),
            "nilai_angka": data.get('skora', '0')
        }]

    pdf.set_font("Times", "", 11)
    for i, item in enumerate(list_nilai, 1):
        angka = item.get('skor') or item.get('nilai_angka', 0)

        pdf.cell(10, 8, str(i), border=1, align="C")
        pdf.cell(100, 8, item.get('mapel', '-'), border=1)
        pdf.cell(40, 8, str(angka), border=1, align="C") 
    pdf.cell(40, 8, terbilang_nilai(angka), border=1, align="C", ln=1)

    total_nilai = 0
    for item in list_nilai:
        # Ambil skor 
        skor = item.get('skor') or item.get('nilai_angka', 0)
        total_nilai += int(skor)

    rata_rata = (total_nilai / len(list_nilai)) if len(list_nilai) > 0 else 0
    
    # Baris Jumlah & Rata-rata
    pdf.set_font("Times", "B", 11)
    pdf.cell(110, 8, "JUMLAH", border=1, align="R")
    pdf.cell(40, 8, str(total_nilai), border=1, align="C")
    pdf.cell(40, 8, "", border=1, ln=1)
    
    pdf.cell(110, 8, "RATA-RATA", border=1, align="R")
    pdf.cell(40, 8, f"{rata_rata:.2f}", border=1, align="C")
    pdf.cell(40, 8, "", border=1, ln=1)
    pdf.ln(10)

    # --- 4. TANGGAL & TANDA TANGAN ---
    tgl_hijri = get_tgl_hijriyah ()
    tgl_masehi = datetime.now().strftime("%d %B %Y")
    tgl_hijri = get_tgl_hijriyah()

    # Lokasi, Tgl Hijriyah & Masehi
    pdf.set_font("Times", "", 11)
    pdf.cell(110)
    pdf.cell(0, 6, f"{data['lokasi']}, {tgl_hijri}", ln=1, align="C")
    pdf.cell(110)
    pdf.cell(0, 6, f"{tgl_masehi}", ln=1, align="C")
    
    pdf.ln(5)
    pdf.cell(110)
    pdf.cell(0, 6, "Kepala Madrasah,", ln=1, align="C")
    pdf.ln(20)
    pdf.cell(110)
    pdf.cell(0, 6, f"( {data['kepala_madrasah']} )", ln=1, align="C")

    # Render ke bytes
    pdf_output = pdf.output()

    if isinstance(pdf_output, bytearray):
        pdf_output = bytes(pdf_output)
    
    return Response(
        content=pdf_output,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Hasil_{data['nama']}.pdf"}
    )