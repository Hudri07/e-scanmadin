from pydantic import BaseModel
from typing import Optional

class HasilUjianBase(BaseModel):
    nomor_peserta: str
    mapel: str
    skor: float
    telegram_file_id: Optional[str] = None

class HasilUjianCreate(HasilUjianBase):
    pass

class HasilUjianResponse(HasilUjianBase):
    id: int

    class Config:
        from_attributes = True