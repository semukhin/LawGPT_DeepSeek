from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class UserOut(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class VerificationRequest(BaseModel):
    email: EmailStr
    code: int

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class RegisterResponse(BaseModel):
    access_token: str
    token_type: str

class CodeVerificationRequest(BaseModel):
    code: int

class VerifyRequest(BaseModel):
    code: int

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: int
    new_password: str
