from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..audit import record
from ..database import get_db
from ..models import Role, User
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from ..security import create_token, hash_password, verify_password

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    role = db.query(Role).filter_by(name="REQUESTER").one()
    user = User(name=data.name, email=data.email, hashed_password=hash_password(data.password), role=role)
    db.add(user)
    db.flush()
    record(db, "CREATE", "users", user.id, user.id)
    db.commit()
    return UserResponse(id=user.id, name=user.name, email=user.email, role=role.name, is_active=user.is_active)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    return TokenResponse(access_token=create_token(user))
