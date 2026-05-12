import itertools
import json
from google import genai
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from app.core.config import settings

# Setup Iterator untuk rotasi kunci
key_cycle = itertools.cycle(settings.api_key_list)

def get_next_client():
    """Fungsi untuk mengambil client dengan kunci API berikutnya"""
    api_key = next(key_cycle)
    return genai.Client(api_key=api_key)

# Fungsi Dekorator Retry (Berlaku untuk semua request AI)
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_fixed(2),
    retry=retry_if_exception_type(Exception)
)

def call_gemini(img, prompt):
    client = get_next_client() # Ambil client baru setiap kali fungsi dijalankan
    return client.models.generate_content(
        model=settings.GEMINI_MODEL_ID,
        contents=[prompt, img],
        config={
            "response_mime_type": "application/json",
            "temperature": 0
        }
    )

def get_data_from_gemini(image_path: str):
    """Fungsi untuk ekstraksi KUNCI JAWABAN."""
    img = Image.open(image_path)
    
    prompt = """
    Ekstrak data dari LJK Madin ini (KUNCI JAWABAN):
    1. mata_pelajaran (string)
    2. kelas (string) Ambil data kelas. WAJIB konversi ke format Angka Romawi diikuti teks dalam kurung dengan huruf kapital di awal (Contoh: "IV (Empat)", "V (Lima)", "VI (Enam)")
    3. jawaban (array of string, contoh: ["A", "B", ...])
    
    Format JSON:
    {
      "mata_pelajaran": "...",
      "kelas": "...",
      "jawaban": ["...", "..."]
    }
    """
    
    try:
        response = call_gemini(img, prompt) # Panggil lewat fungsi retry
        return response.text
    except Exception as e:
        print(f"Error LLM Kunci setelah retry: {e}")
        return json.dumps({"error": str(e)})

def get_identitas_siswa(image_path: str):
    """Fungsi untuk ekstraksi NAMA"""
    img = Image.open(image_path)
    
    prompt = """
    Ekstrak data dari LJK Madin ini.
   
    FORMAT OUTPUT (JSON MURNI):
    {
    "nama": "NAMA LENGKAP SISWA"
    }
    """
    try:
        response = call_gemini(img, prompt) # Panggil lewat fungsi retry
        data = json.loads(response.text)
        return {
            "nama": data.get("nama", "TIDAK TERDETEKSI").upper(),
        }
    except Exception as e:
        print(f"Error LLM Identitas setelah retry: {e}")
        return {"nama": "TIDAK TERDETEKSI"}