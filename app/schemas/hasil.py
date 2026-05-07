from pydantic import BaseModel
from typing import List, Optional

class JawabanDetailSchema(BaseModel):
    no: int
    jawaban: str

class SiswaUpdateHasil(BaseModel):
    nama: str
    nomor_peserta_lama: str  
    nomor_peserta_baru: str
    skor: float
    telegram_message_id: Optional[int] = None
    jawaban_detail: List[JawabanDetailSchema]

class PayloadSimpanHasil(BaseModel):
    mapel: str
    kelas: str
    siswa: List[SiswaUpdateHasil]

class HasilUjianBase(BaseModel):
    nomor_peserta: str
    mapel: str
    skor: float
    telegram_file_id: Optional[str] = None

class HasilUjianResponse(HasilUjianBase):
    id: int
    class Config:
        from_attributes = True