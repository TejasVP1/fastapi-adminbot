from pydantic import BaseModel, EmailStr

class AdminSignup(BaseModel):
    email: EmailStr
    password: str
    name: str

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

