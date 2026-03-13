from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Import helper PASETO
from app.core.security import verify_token 
from app.database.connection import get_db
from app.database.models import UserTable

# Helper class untuk mengambil PASETO dari cookie
class OAuth2PASETOBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str | None:
        # PASETO diawali 'v4.local.'
        token = request.cookies.get("access_token")
        if not token:
            return None
        return token

oauth2_scheme = OAuth2PASETOBearerWithCookie(tokenUrl="/auth/login")

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    # Ambil token dari cookie
    token = request.cookies.get("access_token")
    print(f"--- DEBUG COOKIE: {token}")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Silakan login terlebih dahulu"
        )
    
    # Verifikasi Menggunakan PASETO
    payload = verify_token(token)
    
    if payload is None:
        # Jika verify_token mengembalikan None, berarti expired atau kunci salah
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Sesi tidak valid atau telah kadaluwarsa"
        )
    
    username: str = payload.get("sub") or payload.get("username")
    if username is None:
        raise HTTPException(status_code=401, detail="Format token PASETO salah")

    # Cari user di DB Supabase
    user = db.query(UserTable).filter(UserTable.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User tidak terdaftar")
        
    return user