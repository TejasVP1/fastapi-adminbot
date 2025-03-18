from pydantic import BaseModel, EmailStr
from pydantic import BaseModel, EmailStr, Field

class AdminSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str
    otp: str = Field(..., min_length=6, max_length=6)

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

