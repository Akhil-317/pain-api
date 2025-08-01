from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from utils.jwt_util import decode_token  
from database import get_db
from models.on_boarding_models import User
from utils.jwt_util import oauth2_scheme  

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            raise ValueError("Username not in token.")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def has_permission(user: User, permission_name: str) -> bool:
    if not user.role or not user.role.role_permissions:
        return False
    return any(
        rp.permission and rp.permission.name == permission_name
        for rp in user.role.role_permissions
        if rp.permission.is_active
    )

def permission_required(permission_name: str):
    def dependency(user: User = Depends(get_current_user)):
        if not has_permission(user, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_name}' is required.",
            )
        return user
    return dependency
