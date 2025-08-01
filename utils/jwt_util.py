from datetime import datetime, timedelta
from typing import Optional
from fastapi.security import APIKeyHeader
from jose import jwt, JWTError
from passlib.context import CryptContext
# from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status
from models.on_boarding_models import User

import os
from dotenv import load_dotenv

load_dotenv() 

# === ENV VARS ===
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 180))

# === PASSWORD CONTEXT ===
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# === TOKEN EXTRACTOR ===
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
oauth2_scheme = APIKeyHeader(name="Authorization")

# ================================
# 🔐 Password Utilities
# ================================

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ================================
# Token Generation
# ================================

# def create_access_token(
#     data: dict,
#     expires_delta: Optional[timedelta] = None
# ) -> str:
#     """
#     Creates a JWT access token with an optional expiration time.
#     """
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# ================================
# Rich JWT Token from User Model
# ================================
def create_access_token_for_user(user: User) -> str:
    permissions = [
        {
            "id": rp.permission.id,
            "name": rp.permission.name
        }
        for rp in user.role.role_permissions
        if rp.permission and rp.permission.is_active
    ]

    payload = {
        "sub": user.username,
        "user_id": user.id,
        "user_type": user.user_type.value,
        "role_id": user.role_id,
        "role_name": user.role.role_name,
        "permissions": permissions,
        "exp": int((datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp())
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ================================
# 🔍 Token Decoding
# ================================

def decode_token(token: str) -> dict:
    """
    Decodes the JWT token and returns the payload.
    Raises an error if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
