from fastapi import APIRouter
from app.api.endpoints import auth, profile, koreksi, views, siswa, pdf, excel

# Definisikan Router
api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(koreksi.router, prefix="/api", tags=["Koreksi"])
api_router.include_router(views.router)
api_router.include_router(siswa.router, prefix="/siswa", tags=["Manajamen Siswa"])
api_router.include_router(excel.router, prefix="/unduh", tags=["Ekspor"])
api_router.include_router(pdf.router)