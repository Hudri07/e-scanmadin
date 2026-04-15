from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Any

class Settings(BaseSettings):
    # --- APP SETTINGS ---
    PROJECT_NAME: str = "E-SCAN MADIN"
    API_V1_STR: str = "/api" 
    
    # --- SECURITY SETTINGS (PASETO) ---
    PASETO_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    # --- GEMINI SETTINGS ---
    GEMINI_API_KEY: str
    GEMINI_MODEL_ID: str = "gemini-2.5-flash" 

    # --- DATABASE SETTINGS ---
    DATABASE_URL: str 

    # --- HELPER UNTUK ROTASI KUNCI ---
    @property
    def api_key_list(self) -> List[str]:
        # Mengubah string "KEY1,KEY2,KEY3" menjadi list ["KEY1", "KEY2", "KEY3"]
        return [k.strip() for k in self.GEMINI_API_KEY.split(",") if k.strip()]

    # --- CONFIGURATION ---
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" 
    )

# Inisialisasi settings
settings = Settings()