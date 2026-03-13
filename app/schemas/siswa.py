from pydantic import BaseModel
from typing import Optional

class SiswaBase(BaseModel):
    nomor_peserta: str
    nama: str
    kelas: Optional[str] = None

class SiswaCreate(SiswaBase):
    pass

class SiswaUpdate(BaseModel):
    nama: Optional[str] = None
    kelas: Optional[str] = None