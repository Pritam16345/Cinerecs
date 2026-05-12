"""
CineRecs — Authentication routes.
Register new users and login with JWT tokens.
"""

import logging
from fastapi import APIRouter, HTTPException

from database import get_pool, get_user_by_email, create_user, get_user_by_id
from models import UserCreate, UserLogin, TokenResponse, TokenRefreshRequest
from auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token, 
    decode_token,
    get_token_expired_response
)

logger = logging.getLogger("cinerecs.routes.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(data: UserCreate):
    """
    Register a new user account.
    Hashes password with bcrypt, stores user, returns access and refresh tokens.
    """
    pool = await get_pool()

    # Check if email already exists
    existing = await get_user_by_email(pool, data.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Hash password and create user
    hashed = hash_password(data.password)
    user = await create_user(pool, data.email, hashed)

    # Generate tokens
    access_token = create_access_token(str(user["id"]), data.email)
    refresh_token = create_refresh_token(str(user["id"]))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=str(user["id"]),
        email=data.email,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    """
    Login with email and password. Returns access and refresh tokens.
    """
    pool = await get_pool()

    # Find user by email
    user = await get_user_by_email(pool, data.email)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate tokens
    access_token = create_access_token(str(user["id"]), user["email"])
    refresh_token = create_refresh_token(str(user["id"]))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=str(user["id"]),
        email=user["email"],
    )


@router.post("/refresh")
async def refresh(data: TokenRefreshRequest):
    """
    Refresh access token using a valid refresh token.
    """
    try:
        # Decode and validate refresh token
        payload = decode_token(data.refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        
        # Get user to get their email
        pool = await get_pool()
        user = await get_user_by_id(pool, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        # Create new access token
        new_access_token = create_access_token(user_id, user["email"])
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except HTTPException as e:
        if e.detail == "Token expired":
            raise HTTPException(
                status_code=401,
                detail={"detail": "Refresh token expired", "code": "REFRESH_TOKEN_EXPIRED"}
            )
        raise e
    except Exception as e:
        logger.error(f"Refresh error: {e}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")
