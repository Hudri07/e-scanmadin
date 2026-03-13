from fpdf import FPDF
from fastapi import APIRouter, Response
import io

# Definisikan router
router = APIRouter()

@router.post("/ekspor-pdf")
async def ekspor_pdf(data: dict):
    # Setup PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Header Resmi
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "LEMBAR HASIL UJIAN MADRASAH DINIYAH", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "Sistem Koreksi Otomatis E-SCAN MADIN", ln=True, align="C")
    pdf.line(10, 30, 200, 30) # Garis pembatas
    pdf.ln(15)

    # Data Siswa
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(40, 10, "Nama Siswa", border=0)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f": {data['nama']}", ln=True)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(40, 10, "Nomor Peserta", border=0)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f": {data['nomor_peserta']}", ln=True)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(40, 10, "Mata Pelajaran", border=0)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f": {data.get('mapel', '-')}", ln=True)
    
    pdf.ln(10)

    # Kotak Skor Gede
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 15, f"SKOR AKHIR: {data['skor']}", ln=True, align="C", border=1, fill=True)
    
    # Tanda Tangan
    pdf.ln(20)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(130) # Geser ke kanan
    pdf.cell(0, 10, "Kepala Madrasah,", ln=True, align="C")
    pdf.ln(15)
    pdf.cell(130)
    pdf.cell(0, 10, "( ____________________ )", ln=True, align="C")

    # Render ke bytes
    pdf_output = pdf.output()

    if isinstance(pdf_output, bytearray):
        pdf_output = bytes(pdf_output)
    
    return Response(
        content=pdf_output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Hasil_{data['nama']}.pdf"}
    )