from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models import User

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user: User) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"user_id": user.id, "role": user.role.name, "exp": expires}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret_key, algorithms=[get_settings().jwt_algorithm])
        user_id = int(payload.get("user_id"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no autorizado")
    return user


def require_roles(*roles: str):
    def guard(user: User = Depends(current_user)):
        if user.role.name not in roles:
            raise HTTPException(status_code=403, detail="No tiene permisos para esta operación")
        return user
    return guard
