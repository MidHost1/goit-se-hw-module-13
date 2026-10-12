from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.services.cache import get_cached_user, set_cached_user
import hashlib
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.database.db import get_db
from src.database.models import User
from src.conf.config import settings

bearer_scheme = HTTPBearer()   # замість oauth2_scheme = OAuth2PasswordBearer(...)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[float] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (timedelta(minutes=expires_delta) if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire, "scope": "access_token"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict, expires_delta: Optional[float] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (timedelta(days=expires_delta) if expires_delta else timedelta(days=7))
    to_encode.update({"exp": expire, "scope": "refresh_token"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_email_token(data: dict, scope: str = "email_verification",
                       expires_delta: timedelta = timedelta(days=7)) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "scope": scope})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_email_token(token: str, scope: str = "email_verification") -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Invalid or expired token")
    if payload.get("scope") != scope or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid token scope")
    return payload


def get_email_from_token(token: str, scope: str = "email_verification") -> str:
    return decode_email_token(token, scope)["sub"]


def password_fingerprint(hashed_password: str) -> str:
    # відбиток поточного пароля: після зміни пароля старі reset-токени стають недійсними
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                     db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        scope: str = payload.get("scope")
        if email is None or scope != "access_token":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    cached = get_cached_user(email)
    if cached:
        return User(**cached)

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    set_cached_user(user)
    return user