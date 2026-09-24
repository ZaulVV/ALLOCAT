from fastapi import APIRouter, Depends
from ..models import User
from ..schemas import UserResponse
from ..security import current_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return UserResponse(id=user.id, name=user.name, email=user.email, role=user.role.name, is_active=user.is_active)
