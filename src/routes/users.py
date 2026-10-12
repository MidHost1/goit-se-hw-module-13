import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from src.conf.config import settings
from src.database.db import get_db
from src.database.models import User
from src.schemas.user import UserDetailSchema
from src.services.auth import get_current_user
from src.services.cache import invalidate_user

router = APIRouter(prefix="/users", tags=["users"])

cloudinary.config(
    cloud_name=settings.cloudinary_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)


@router.get("/me", response_model=UserDetailSchema)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/avatar", response_model=UserDetailSchema)
def update_avatar(
    file: UploadFile = File(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")

    public_id = f"ContactsApp/user_{current_user.id}"
    r = cloudinary.uploader.upload(file.file, public_id=public_id, overwrite=True)
    src_url = cloudinary.CloudinaryImage(public_id).build_url(
        width=250, height=250, crop="fill", version=r.get("version")
    )

    user = db.query(User).filter(User.id == current_user.id).first()
    user.avatar = src_url
    db.commit()
    db.refresh(user)
    invalidate_user(user.email)
    return user