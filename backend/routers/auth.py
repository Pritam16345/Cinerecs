"""
CineRecs — Authentication routes.
Register new users and login with JWT tokens.
"""

import logging
from fastapi import APIRouter, HTTPException

from database import get_pool, get_user_by_email, create_user
from models import UserCreate, UserLogin, TokenResponse
from auth import hash_password, verify_password, create_token

logger = logging.getLogger("cinerecs.routes.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(data: UserCreate):
    """
    Register a new user account.
    Hashes password with bcrypt, stores user, returns JWT.
    """
    pool = await get_pool()

    # Check if email already exists
    existing = await get_user_by_email(pool, data.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Hash password and create user
    hashed = hash_password(data.password)
    user = await create_user(pool, data.email, hashed)

    # Generate JWT
    token = create_token(str(user["id"]), data.email)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user["id"]),
        email=data.email,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    """
    Login with email and password. Returns JWT token (expires in 7 days).
    """
    pool = await get_pool()

    # Find user by email
    user = await get_user_by_email(pool, data.email)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate JWT
    token = create_token(str(user["id"]), data.email)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user["id"]),
        email=user["email"],
    )
