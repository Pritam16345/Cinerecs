"""
CineRecs — Authentication module.
JWT token creation/verification and bcrypt password hashing.
"""

import os
import logging
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger("cinerecs.auth")

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-please")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_token(user_id: str, email: str) -> str:
    """
    Create a JWT token with user_id and email claims.
    Expires in JWT_EXPIRE_DAYS (default 7 days).
    """
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Returns the payload dict or raises HTTPException.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token: no subject")
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """
    FastAPI dependency: extract and validate JWT from Authorization header.
    Returns dict with 'user_id' and 'email'.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = decode_token(credentials.credentials)
    return {
        "user_id": payload["sub"],
        "email": payload.get("email", ""),
    }


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict | None:
    """
    FastAPI dependency: extract JWT if present, return None if not.
    Used for endpoints that show extra content for logged-in users.
    """
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return {
            "user_id": payload["sub"],
            "email": payload.get("email", ""),
        }
    except HTTPException:
        return None
