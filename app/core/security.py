import os
import json
from datetime import datetime, timedelta, timezone
from pyseto import Key, Paseto
from passlib.context import CryptContext 
from dotenv import load_dotenv

load_dotenv()

# Ambil Secret Key PASETO dari .env
PASETO_SECRET = os.getenv("PASETO_SECRET")
if not PASETO_SECRET or len(PASETO_SECRET) != 32:
    raise ValueError("PASETO_SECRET harus tepat 32 karakter!")

KEY = Key.new(version=4, purpose="local", key=PASETO_SECRET.encode())

# --- FUNGSI PASSWORD ---

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifikasi password menggunakan Argon2"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Generate hash Argon2"""
    return pwd_context.hash(password)


# --- FUNGSI PASETO ---

def create_access_token(data: dict):
    minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    
    payload = {
        **data,
        "exp": expire.isoformat() 
    }
    
    p = Paseto()
    token = p.encode(KEY, payload)
    return token.decode()

def verify_token(token: str):
    try:
        # Pastikan token adalah bytes sebelum masuk ke p.decode
        if isinstance(token, str):
            token = token.encode("utf-8")
            
        p = Paseto()
        decoded = p.decode(KEY, token)
        
        # decoded.payload itu BYTES (JSON string). 
        payload = json.loads(decoded.payload)
        
        # Cek "exp" karena payload sudah jadi dict
        if "exp" in payload:
            exp_time = datetime.fromisoformat(payload["exp"])
            if datetime.now(timezone.utc) > exp_time:
                print("--- DEBUG: Token Expired")
                return None
                
        return payload
    except Exception as e:
        print(f"--- DEBUG PASETO ERROR: {e}")
        return None