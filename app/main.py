import os
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

# Import Internal
from app.api.router import api_router
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.exceptions import unauthorized_handler, forbidden_handler 
from app.database import models
from app.database.connection import engine, get_db


app = FastAPI(title=settings.PROJECT_NAME)

# Buat tabel saat startup
@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(bind=engine)

# Setup Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Daftarkan Global Exception Handler
app.add_exception_handler(401, unauthorized_handler)
app.add_exception_handler(403, forbidden_handler)

# --- REGISTER ROUTERS ---
app.include_router(api_router)
