from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.services.database import admins_collection
from app.models.admin import AdminSignup, AdminLogin
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login/")

# Hash Password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Verify Password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Create JWT Token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

# Admin Signup
async def admin_signup(admin: AdminSignup):
    existing_admin = admins_collection.find_one({"email": admin.email})
    if existing_admin:
        return {"error": "Admin already exists!"}

    hashed_password = hash_password(admin.password)
    admin_data = {"email": admin.email, "password": hashed_password, "created_at": datetime.utcnow()}
    admins_collection.insert_one(admin_data)
    return {"message": "Admin registered successfully!"}

# Admin Login
async def admin_login(email, password):
    admin = admins_collection.find_one({"email": email})
    if not admin or not verify_password(password, admin["password"]):
        return None

    admin_id = str(admin["_id"])
    token_data = {"sub": email, "admin_id": admin_id, "exp": datetime.utcnow() + timedelta(minutes=60)}
    access_token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return {"access_token": access_token, "token_type": "bearer"}

# Secure other endpoints
async def get_current_admin(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        admin_id: str = payload.get("admin_id")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"email": email, "admin_id": admin_id}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# from passlib.context import CryptContext
# from datetime import datetime
# from app.services.database import admins_collection
# from app.models.admin import AdminSignup, AdminLogin
# from datetime import datetime, timedelta
# from bson import ObjectId 
# from jose import jwt
# from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM
# # Password hashing setup
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# async def admin_signup(admin: AdminSignup):
#     """Registers an admin in MongoDB Atlas"""
#     existing_admin = admins_collection.find_one({"email": admin.email})
#     if existing_admin:
#         return {"error": "Admin already exists!"}

#     hashed_password = pwd_context.hash(admin.password)
#     admin_data = {
#         "email": admin.email,
#         "password": hashed_password,
#         "created_at": datetime.utcnow()
#     }
#     admins_collection.insert_one(admin_data)  # Save to MongoDB
#     return {"message": "Admin registered successfully!"}

# async def admin_login(email, password):
#     """Authenticates an admin and returns a JWT token"""
#     admin = admins_collection.find_one({"email": email})
#     # Convert ObjectId to string for JWT payload
#     admin_id = str(admin["_id"])
#     if not admin or not pwd_context.verify(password, admin["password"]):
#         return None  # Invalid login

    
#     token_data = {"sub": email,"admin_id": admin_id, "exp": datetime.utcnow() + timedelta(minutes=60)}
#     access_token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
#     return {"access_token": access_token, "token_type": "bearer"}
