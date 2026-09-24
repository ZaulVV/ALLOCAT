from sqlalchemy.orm import Session
from .models import AuditLog


def record(db: Session, action: str, table_name: str, record_id: int | None, user_id: int | None, details=None):
    db.add(AuditLog(action=action, table_name=table_name, record_id=record_id, user_id=user_id, details=details))
