from google import genai
import json
from PIL import Image
from app.core.config import settings

# Inisialisasi client menggunakan library google-genai
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Konfigurasi model 
MODEL_ID = "gemini-2.5-flash" 

def get_data_from_gemini(image_path: str):
    """Fungsi untuk ekstraksi KUNCI JAWABAN."""
    img = Image.open(image_path)
    
    prompt = """
    Ekstrak data dari LJK Madin ini (KUNCI JAWABAN):
    1. mata_pelajaran (string)
    2. kelas (string)
    3. jawaban (array of string, contoh: ["A", "B", ...])
    
    Format JSON:
    {
      "mata_pelajaran": "...",
      "kelas": "...",
      "jawaban": ["...", "..."]
    }
    """
    
    try:
        # panggil library google-genai
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt, img],
            config={
                "response_mime_type": "application/json",
                "temperature": 0
            }
        )
        return response.text
    except Exception as e:
        print(f"Error LLM Kunci: {e}")
        return json.dumps({"error": str(e)})

def get_identitas_siswa(image_path: str):
    """Fungsi untuk ekstraksi NAMA & NOMOR PESERTA."""
    img = Image.open(image_path)
    
    prompt = """
    Analisis gambar LJK ini dan ekstrak informasi identitas siswa.
    Kembalikan data dalam format JSON murni:
    {
      "nama": "NAMA LENGKAP SISWA",
      "nomor_peserta": "NOMOR/ANGKA"
    }
    Jika tidak terbaca, tulis "TIDAK TERDETEKSI".
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt, img],
            config={
                "response_mime_type": "application/json",
                "temperature": 0
            }
        )
        
        # Bersihkan response dan muat sebagai JSON
        data = json.loads(response.text)
        
        return {
            "nama": data.get("nama", "TIDAK TERDETEKSI").upper(),
            "nomor_peserta": data.get("nomor_peserta", "-")
        }
    except Exception as e:
        print(f"Error LLM Identitas: {e}")
        return {"nama": "TIDAK TERDETEKSI", "nomor_peserta": "-"}