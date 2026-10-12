from pydantic import BaseModel, ConfigDict, EmailStr, Field

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

class RequestEmailSchema(BaseModel):
    email: EmailStr

class UserDetailSchema(BaseModel):
    id: int
    email: EmailStr
    avatar: str | None = None

    model_config = ConfigDict(from_attributes=True)

class ResetPasswordSchema(BaseModel):
    new_password: str = Field(min_length=6, max_length=50)