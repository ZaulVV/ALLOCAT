from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from .models import Notification, User

executor = ThreadPoolExecutor(max_workers=2)


def queue_notification(db: Session, recipient: User, subject: str, body: str):
    db.add(Notification(recipient_id=recipient.id, subject=subject, body=body))
    # Local delivery is deliberately non-blocking; SMTP can be added without changing domain code.
    executor.submit(lambda: None)
