import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from jose import jwt
from fastapi.exceptions import HTTPException
from app.services.auth_services import (
    hash_password, verify_password, create_access_token,
    admin_login, get_current_admin
)
from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM

@pytest.fixture
def mock_admins_collection():
    """Mock MongoDB admins collection"""
    with patch("app.services.auth_services.admins_collection") as mock_collection:
        yield mock_collection

def test_hash_password():
    """Test password hashing"""
    password = "securepassword"
    hashed = hash_password(password)
    assert hashed != password  # Hashed password should not match plain text
    assert verify_password(password, hashed)  # Should verify correctly

def test_verify_password():
    """Test password verification"""
    password = "securepassword"
    hashed = hash_password(password)
    assert verify_password(password, hashed)  # Correct password
    assert not verify_password("wrongpassword", hashed)  # Incorrect password

def test_create_access_token():
    """Test JWT token creation"""
    data = {"sub": "test@example.com"}
    token = create_access_token(data, timedelta(minutes=30))
    
    decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    assert decoded["sub"] == "test@example.com"
    assert "exp" in decoded

@pytest.mark.asyncio
async def test_admin_login_success(mock_admins_collection):
    """Test successful admin login with JWT token"""
    hashed_password = hash_password("password123")
    mock_admins_collection.find_one.return_value = {
        "email": "admin@example.com",
        "password": hashed_password,
        "_id": "123456"  # Mock admin ID
    }

    response = await admin_login("admin@example.com", "password123")

    assert response is not None, "Admin login should return a valid response"
    assert "access_token" in response
    assert response["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_admin_login_invalid_password(mock_admins_collection):
    """Test login fails with incorrect password"""
    hashed_password = hash_password("password123")
    mock_admins_collection.find_one.return_value = {
        "email": "admin@example.com",
        "password": hashed_password
    }

    response = await admin_login("admin@example.com", "wrongpassword")
    assert response is None  # Should return None for invalid password

@pytest.mark.asyncio
async def test_admin_login_non_existent_admin(mock_admins_collection):
    """Test login fails when admin does not exist"""
    mock_admins_collection.find_one.return_value = None

    response = await admin_login("nonexistent@example.com", "password123")
    assert response is None  # Should return None for non-existent admin

@pytest.mark.asyncio
async def test_get_current_admin_valid_token():
    """Test retrieving admin info from a valid token"""
    admin_data = {"sub": "admin@example.com", "admin_id": "123"}
    token = create_access_token(admin_data)

    result = await get_current_admin(token)
    
    assert result["email"] == "admin@example.com"
    assert result["admin_id"] == "123"

@pytest.mark.asyncio
async def test_get_current_admin_invalid_token():
    """Test handling of an invalid token"""
    invalid_token = "invalid.token.here"

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(invalid_token)

    assert exc_info.value.status_code == 401
    assert "Invalid token" in exc_info.value.detail
