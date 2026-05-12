import os
import logging
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger("cinerecs.auth")

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-please")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, email: str) -> str:
    """Create a short-lived access token (30 minutes)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token (7 days)."""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict:
    """
    Decode and validate a JWT token.
    Returns the payload dict or raises HTTPException with specific code.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Validate token type
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=401, 
                detail=f"Invalid token type: expected {expected_type}"
            )
            
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token: no subject")
            
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, 
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token") from None


# Override the default 401 response for expired tokens in a middleware or exception handler
# but since the user specifically asked for a JSON response with code: TOKEN_EXPIRED,
# we'll catch the HTTPException in the router or implement a custom handler.
# Actually, the user said: return a JSON response with {"detail": "Token expired", "code": "TOKEN_EXPIRED"}

def get_token_expired_response():
    return {
        "detail": "Token expired",
        "code": "TOKEN_EXPIRED"
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """
    FastAPI dependency: extract and validate JWT from Authorization header.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        return {
            "user_id": payload["sub"],
            "email": payload.get("email", ""),
        }
    except HTTPException as e:
        if e.detail == "Token expired":
            # Return the specific format requested
            raise HTTPException(
                status_code=401,
                detail=get_token_expired_response()
            )
        raise e


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict | None:
    """
    FastAPI dependency: extract JWT if present, return None if not.
    """
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        return {
            "user_id": payload["sub"],
            "email": payload.get("email", ""),
        }
    except Exception:
        return None
