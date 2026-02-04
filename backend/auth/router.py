"""
Authentication routes: login, logout, register, users, verify.
"""
from fastapi import APIRouter, HTTPException

from backend.auth.auth_backend import auth_backend
from backend.auth.users import fastapi_users
from backend.database.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="", tags=["auth"])

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    tags=["auth"],
)


@router.post("/verify")
async def verify_email_placeholder():
    """Placeholder for future email verification endpoint."""
    raise HTTPException(status_code=501, detail="Email verification will be implemented in a future phase")
