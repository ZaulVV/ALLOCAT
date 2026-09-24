from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import AuditLog, User
from ..security import require_roles

router = APIRouter()


@router.get("", response_model=list[dict])
def logs(db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "AUDITOR"))):
    return [{"id": x.id, "action": x.action, "table_name": x.table_name, "record_id": x.record_id, "user_id": x.user_id, "timestamp": x.timestamp, "details": x.details} for x in db.query(AuditLog).order_by(AuditLog.id.desc()).all()]
