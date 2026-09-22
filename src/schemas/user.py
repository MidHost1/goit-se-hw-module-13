from pydantic import BaseModel, EmailStr

# Те, що приходить від клієнта при реєстрації/логіні
class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str

# Логін
class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

# Те, що сервер повертає клієнту (Без хешованого паролю)
class UserResponseSchema(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True

# Формат відповіді після успішного логіну
class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"