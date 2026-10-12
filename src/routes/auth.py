from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, status, Security, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from src.database.db import get_db
from src.database.models import User
from src.schemas.user import (
    UserRegisterSchema, UserResponseSchema, TokenSchema, UserLoginSchema,
    RequestEmailSchema, ResetPasswordSchema,
)
from src.services.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_email_from_token,
    decode_email_token,
    password_fingerprint,
)
from src.services.email import send_email, send_reset_password_email
from src.services.limiter import limiter
from src.conf.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

RESET_PAGE = (Path(__file__).resolve().parent.parent / "services" / "templates"
              / "reset_password_page.html").read_text(encoding="utf-8")


@router.post("/signup", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
def signup(body: UserRegisterSchema, background_tasks: BackgroundTasks, request: Request,
           db: Session = Depends(get_db)):
    exist_user = db.query(User).filter(User.email == body.email).first()
    if exist_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")

    new_user = User(
        email=body.email,
        password=get_password_hash(body.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    background_tasks.add_task(send_email, new_user.email, str(request.base_url))
    return new_user


@router.post("/login", response_model=TokenSchema)
def login(body: UserLoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if user is None or not verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.confirmed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed")

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    user.refresh_token = refresh_token
    db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get("/refresh_token", response_model=TokenSchema)
def refresh_token(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("scope") != "refresh_token":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scope for token")
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    user = db.query(User).filter(User.email == email).first()
    if user is None or user.refresh_token != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = create_access_token(data={"sub": email})
    new_refresh_token = create_refresh_token(data={"sub": email})

    user.refresh_token = new_refresh_token
    db.commit()

    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


@router.get("/confirmed_email/{token}")
def confirmed_email(token: str, db: Session = Depends(get_db)):
    email = get_email_from_token(token)
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error")
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    user.confirmed = True
    db.commit()
    return {"message": "Email confirmed"}


@router.post("/request_email")
def request_email(body: RequestEmailSchema, background_tasks: BackgroundTasks, request: Request,
                  db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if user and user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user:
        background_tasks.add_task(send_email, user.email, str(request.base_url))
    return {"message": "Check your email for confirmation."}


@router.post("/request_password_reset", description="No more than 3 requests per minute")
@limiter.limit("3/minute")
def request_password_reset(request: Request, body: RequestEmailSchema, background_tasks: BackgroundTasks,
                           db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if user:
        background_tasks.add_task(
            send_reset_password_email, user.email, str(request.base_url), password_fingerprint(user.password)
        )
    # відповідь однакова, чи існує такий email, чи ні
    return {"message": "If this email is registered, you will receive reset instructions."}


@router.get("/reset_password/{token}", response_class=HTMLResponse, include_in_schema=False)
def reset_password_form(token: str):
    return RESET_PAGE


@router.post("/reset_password/{token}")
def reset_password(token: str, body: ResetPasswordSchema, db: Session = Depends(get_db)):
    payload = decode_email_token(token, scope="password_reset")
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if user is None or payload.get("pwd") != password_fingerprint(user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already used token")

    user.password = get_password_hash(body.new_password)
    user.refresh_token = None  # старі refresh-токени більше не діють
    db.commit()
    return {"message": "Password updated successfully"}