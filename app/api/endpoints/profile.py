from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import UserTable
from app.api.dependencies import get_current_user
from passlib.context import CryptContext

router = APIRouter()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Update Data Dasar (Nama & Email)
@router.post("/update")
async def update_profile(
    full_name: str = Form(...),
    email: str = Form(None),
    db: Session = Depends(get_db),
    user: UserTable = Depends(get_current_user)
):
    try:
        user.full_name = full_name
        user.email = email
        db.commit()
        return {"status": "success", "message": "Profil berhasil diperbarui"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Gagal memperbarui profil")

# Update Password
@router.post("/change-password")
async def update_password(
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    user: UserTable = Depends(get_current_user)
):
    try:
        # Hash password baru
        user.hashed_password = pwd_context.hash(new_password)
        db.commit()
        return {"status": "success", "message": "Password berhasil diganti"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Gagal mengganti password")