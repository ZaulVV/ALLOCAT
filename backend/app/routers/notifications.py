from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Notification, User
from ..security import current_user

router = APIRouter()


@router.get("")
def list_notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(Notification).filter_by(recipient_id=user.id).order_by(Notification.id.desc()).all()
