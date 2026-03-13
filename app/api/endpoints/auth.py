from fastapi import APIRouter, Depends, HTTPException, status, Response, Form
from sqlalchemy.orm import Session
from app.core import security
from app.core.config import settings
from app.schemas.token import Token
from app.database.connection import get_db
from app.database.models import UserTable
from fastapi.responses import JSONResponse

# Definisikan Router
router = APIRouter()

@router.post("/login")
async def login(
    response: Response, 
    username: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    # Cari user di Supabase
    user = db.query(UserTable).filter(UserTable.username == username).first()
    
    # Verifikasi Password
    if not user or not security.verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username atau password salah"
        )
    
    # Buat PASETO Token
    access_token = security.create_access_token(
        data={"sub": user.username}
    )
    
    # Simpan ke Cookie
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True, 
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        path="/",
        secure=False 
    )

    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }
    
@router.post("/logout")
async def logout(response: Response):
    # Hapus cookie
    res = JSONResponse(content={"status": "success", "message": "Logged out"})
    res.delete_cookie(
        key="access_token",
        path="/",   
        httponly=True,
        samesite="lax" 
    )
    return res