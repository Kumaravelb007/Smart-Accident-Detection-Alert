"""
Authentication API Routes
Handles user signup, login, and logout.
"""

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from utils.auth import signup, login, logout

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup")
async def api_signup(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    """Register a new user account."""
    result = signup(name, email, password)
    status = 200 if result["success"] else 400
    return JSONResponse(content=result, status_code=status)


@router.post("/login")
async def api_login(
    email: str = Form(...),
    password: str = Form(...),
):
    """Login with email and password."""
    result = login(email, password)
    status = 200 if result["success"] else 401
    return JSONResponse(content=result, status_code=status)


@router.post("/logout")
async def api_logout(token: str = Form("")):
    """Logout and invalidate session."""
    logout(token)
    return {"success": True, "message": "Logged out."}
