from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.services.database import admins_collection
from app.models.admin import AdminSignup, AdminLogin
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM
import logging
import traceback

# Configure logging
logger = logging.getLogger(__name__)

# Configure password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configure OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login/")

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt algorithm"""
    try:
        hashed_password = pwd_context.hash(password)
        logger.debug("Password hashed successfully")
        return hashed_password
    except Exception as e:
        logger.error(f"Password hashing failed: {str(e)}")
        logger.debug(traceback.format_exc())
        raise ValueError("Failed to hash password") from e

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plaintext password matches the hashed version"""
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.debug(f"Password verification result: {'success' if is_valid else 'failure'}")
        return is_valid
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create a JWT access token with expiration time"""
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=60))
        to_encode.update({"exp": expire})
        token = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.debug(f"Access token created for user: {data.get('sub', 'unknown')}")
        return token
    except Exception as e:
        logger.error(f"Token creation failed: {str(e)}")
        logger.debug(traceback.format_exc())
        raise ValueError("Failed to create access token") from e

async def admin_signup(admin: AdminSignup):
    """Register a new admin in the database with hashed password"""
    try:
        logger.info(f"Processing signup for new admin: {admin.email}")
        
        # Check if admin already exists
        try:
            existing_admin = admins_collection.find_one({"email": admin.email})
            if existing_admin:
                logger.warning(f"Signup failed: Admin {admin.email} already exists")
                return {"error": "Admin already exists!"}
        except Exception as db_error:
            logger.error(f"Database error checking existing admin: {str(db_error)}")
            logger.debug(traceback.format_exc())
            raise ValueError("Failed to check if admin exists") from db_error

        # Hash password and create admin record
        try:
            hashed_password = hash_password(admin.password)
            admin_data = {
                "email": admin.email, 
                "password": hashed_password, 
                "name": admin.name, 
                "created_at": datetime.utcnow()
            }
            result = admins_collection.insert_one(admin_data)
            if not result.acknowledged:
                logger.error("Database insertion failed for new admin")
                raise ValueError("Failed to insert new admin record")
                
            logger.info(f"Admin registered successfully: {admin.email}")
            return {"message": "Admin registered successfully!"}
        except ValueError as ve:
            # Re-raise ValueErrors (like from hash_password)
            raise ve
        except Exception as e:
            logger.error(f"Admin registration error: {str(e)}")
            logger.debug(traceback.format_exc())
            raise ValueError("Failed to register admin") from e
    except ValueError as ve:
        # Convert ValueErrors to a standardized error response
        return {"error": str(ve)}
    except Exception as e:
        logger.error(f"Unexpected error during admin signup: {str(e)}")
        logger.debug(traceback.format_exc())
        return {"error": "Internal server error during signup"}

async def admin_login(email, password):
    """Authenticate an admin and return a JWT token if successful"""
    try:
        logger.info(f"Login attempt for admin: {email}")
        
        # Find admin in database
        try:
            admin = admins_collection.find_one({"email": email})
            if not admin:
                logger.warning(f"Login failed: Admin {email} not found")
                return None
        except Exception as db_error:
            logger.error(f"Database error finding admin: {str(db_error)}")
            logger.debug(traceback.format_exc())
            raise ValueError("Failed to retrieve admin data") from db_error

        # Verify password
        try:
            if not verify_password(password, admin["password"]):
                logger.warning(f"Login failed: Invalid password for {email}")
                return None
        except Exception as verify_error:
            logger.error(f"Password verification error: {str(verify_error)}")
            logger.debug(traceback.format_exc())
            raise ValueError("Failed to verify password") from verify_error

        # Create and return JWT token
        try:
            admin_id = str(admin["_id"])
            token_data = {
                "sub": email, 
                "admin_id": admin_id, 
                "exp": datetime.utcnow() + timedelta(minutes=60)
            }
            access_token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
            logger.info(f"Login successful for admin: {email}")
            return {"access_token": access_token, "token_type": "bearer"}
        except Exception as token_error:
            logger.error(f"Token creation error: {str(token_error)}")
            logger.debug(traceback.format_exc())
            raise ValueError("Failed to create authentication token") from token_error
    except Exception as e:
        logger.error(f"Unexpected error during admin login: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

async def get_current_admin(token: str = Depends(oauth2_scheme)):
    """Validate the JWT token and return the admin information"""
    try:
        logger.debug("Validating authentication token")
        
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            email: str = payload.get("sub")
            admin_id: str = payload.get("admin_id")
            
            if not email or not admin_id:
                logger.warning("Invalid token: missing required claims")
                raise HTTPException(status_code=401, detail="Invalid token")
                
            logger.debug(f"Token validation successful for admin: {email}")
            return {"email": email, "admin_id": admin_id}
        except JWTError as jwt_error:
            logger.warning(f"JWT validation failed: {str(jwt_error)}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            logger.debug(traceback.format_exc())
            raise HTTPException(status_code=401, detail="Authentication failed")
    except HTTPException as he:
        # Re-raise HTTP exceptions as they're already handled
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in authentication: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error during authentication")