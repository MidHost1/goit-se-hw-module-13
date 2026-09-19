from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional


class ContactSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    birthday: date
    additional_info: Optional[str] = None


class ContactResponseSchema(ContactSchema):
    id: int

    class Config:
        from_attributes = True