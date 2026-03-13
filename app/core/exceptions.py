from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

async def unauthorized_handler(request: Request, exc: HTTPException):
    return RedirectResponse(url="/login")

async def forbidden_handler(request: Request, exc: HTTPException):
    return RedirectResponse(url="/login")