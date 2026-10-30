import hashlib
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
import jwt
from app.core.config import settings

def get_password_hash(password: str) -> str:
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return f"{salt}${hashed}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if "$" not in hashed_password:
        return False
    salt, expected_hash = hashed_password.split("$", 1)
    actual_hash = hashlib.sha256(f"{salt}{plain_password}".encode("utf-8")).hexdigest()
    return actual_hash == expected_hash

def create_access_token(user_id: Any, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    payload = {
        "sub": str(user_id),
        "user_id": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

