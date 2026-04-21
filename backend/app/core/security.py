from datetime import datetime, timedelta, timezone
import base64
import hashlib

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
_BCRYPT_MAX_BYTES = 72


def _normalize_password(password: str) -> bytes:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) <= _BCRYPT_MAX_BYTES:
        return password_bytes

    digest = hashlib.sha256(password_bytes).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    normalized = _normalize_password(password)
    return bcrypt.hashpw(normalized, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    normalized = _normalize_password(plain)
    return bcrypt.checkpw(normalized, hashed.encode("utf-8"))


def create_access_token(
    data: dict,
    expires_delta: timedelta = timedelta(hours=24),
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    return payload
