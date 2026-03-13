from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.sql import func
from .connection import Base

class UserTable(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)    
    full_name = Column(String)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)

class SiswaTable(Base):
    __tablename__ = "siswa"
    nomor_peserta = Column(String, primary_key=True)
    nama = Column(String, nullable=False)
    kelas = Column(String, nullable=False)

class KunciJawabanTable(Base):
    __tablename__ = "kunci_jawaban"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mapel = Column(String, nullable=False)
    kelas = Column(String, nullable=False)
    kunci_json = Column(Text, nullable=False)

class HasilUjianTable(Base):
    __tablename__ = "hasil_ujian"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nomor_peserta = Column(String, ForeignKey("siswa.nomor_peserta", onupdate="CASCADE"))
    mapel = Column(String)
    skor = Column(Float)
    tanggal = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('nomor_peserta', 'mapel', name='_siswa_mapel_uc'),)