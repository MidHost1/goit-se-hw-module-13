from typing import List
from fastapi import APIRouter, HTTPException, Depends, Request, status
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import Contact, User
from src.schemas.contact import ContactSchema, ContactResponseSchema
from src.services.auth import get_current_user
from src.services.limiter import limiter

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("/", response_model=ContactResponseSchema, status_code=status.HTTP_201_CREATED,
             description="No more than 5 requests per minute")
@limiter.limit("5/minute")
def create_contact(
    request: Request,
    body: ContactSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contact = Contact(**body.model_dump(), user_id=current_user.id)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/", response_model=List[ContactResponseSchema],
            description="No more than 30 requests per minute")
@limiter.limit("30/minute")
def get_contacts(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Contact).filter(Contact.user_id == current_user.id).offset(skip).limit(limit).all()


@router.get("/{contact_id}", response_model=ContactResponseSchema,
            description="No more than 30 requests per minute")
@limiter.limit("30/minute")
def get_contact(
    request: Request,
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == current_user.id).first()
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.put("/{contact_id}", response_model=ContactResponseSchema,
            description="No more than 10 requests per minute")
@limiter.limit("10/minute")
def update_contact(
    request: Request,
    contact_id: int,
    body: ContactSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == current_user.id).first()
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    for key, value in body.model_dump().items():
        setattr(contact, key, value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT,
               description="No more than 10 requests per minute")
@limiter.limit("10/minute")
def delete_contact(
    request: Request,
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == current_user.id).first()
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    db.delete(contact)
    db.commit()
    return None