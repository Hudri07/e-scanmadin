import httpx
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_to_telegram(file_content: bytes, filename: str, caption: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    async with httpx.AsyncClient() as client:
        files = {'photo': (filename, file_content) }
        data = {
            'chat_id': TELEGRAM_CHAT_ID, 
            'caption': caption, 
            'parse_mode': 'Markdown' }
        try:
            response = await client.post(url, data=data, files=files)
            res_json = response.json()
            if res_json.get("ok"):
                # Ambil message_id dari response telegram
                return res_json["result"]["message_id"]
            return None
        except Exception as e:
            print(f"Telegram Upload Error: {e}")
            return None

async def edit_telegram_caption(message_id: int, caption: str):
    """Mengubah teks caption pada foto yang sudah terkirim sebelumnya"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageCaption"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "message_id": message_id,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

