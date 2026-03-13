from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # --- APP SETTINGS ---
    PROJECT_NAME: str = "E-SCAN MADIN"
    API_V1_STR: str = "/api" 
    
    # --- SECURITY SETTINGS (PASETO) ---
    PASETO_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    # --- GEMINI SETTINGS ---
    GEMINI_API_KEY: str

    # --- DATABASE SETTINGS ---
    DATABASE_URL: str 

    # --- CONFIGURATION ---
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" 
    )

# Inisialisasi settings
settings = Settings()