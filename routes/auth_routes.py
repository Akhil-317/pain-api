from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from datetime import timedelta, datetime

from utils.jwt_util import verify_password, get_password_hash, oauth2_scheme, decode_token, create_access_token_for_user
from database import get_db
from models.on_boarding_models import User
from schemas.on_boarding_schemas import UserRegisterRequest
from utils.redis_util import redis_client

router = APIRouter(tags=["Auth"])

# === REGISTER ENDPOINT ===
@router.post("/register", summary="Register a new user")
def register_user(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    # Check if user with username or email already exists
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.emailid == request.emailid).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(request.password)

    new_user = User(
        username=request.username,
        emailid=request.emailid,
        phonenumber=request.phonenumber,
        password=hashed_password,
        user_type=request.user_type,
        role_id=request.role_id,
        is_active=True,
        created_at=datetime.utcnow(),
        created_by="system"  # or current user if available
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "username": new_user.username,
        "email": new_user.emailid,
        "role_id": new_user.role_id
    }



# === LOGIN ENDPOINT ===
@router.post("/login", summary="Login and get JWT token")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive or blocked.",
        )

    access_token = create_access_token_for_user(user)

    # Optional: Update last_login_at
    user.last_login_at = datetime.utcnow()
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "user_type": user.user_type,
        "role_id": user.role_id,
    }

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Decodes JWT, checks Redis blacklist (if used), and returns the User.
    """
    # Check Redis token blacklist (if implemented)
    if redis_client.get(f"blacklist:{token}") == "true":
        raise HTTPException(status_code=401, detail="Token has been revoked")

    # Decode token
    payload = decode_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Get user from DB
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user

@router.post("/logout", summary="Logout user")
def logout(
    token: str = Depends(oauth2_scheme),
    current_user=Depends(get_current_user)
):
    redis_client.setex(f"blacklist:{token}", 10800, "true")  # Store token in Redis for 3 hours
    return {"message": "Logout successful. Token is blacklisted."}

