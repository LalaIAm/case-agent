"""
FastAPI-Users instance and current-user dependency.
"""
from uuid import UUID

from fastapi_users import FastAPIUsers

from backend.auth.auth_backend import auth_backend
from backend.auth.user_manager import UserManager, get_user_manager
from backend.database.models import User

fastapi_users = FastAPIUsers[User, UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
