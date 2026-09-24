from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..audit import record
from ..database import get_db
from ..models import Reservation, Resource, User
from ..notifications import queue_notification
from ..schemas import ReservationCreate, ReservationDecision, ReservationResponse
from ..security import current_user, require_roles

router = APIRouter()


@router.get("", response_model=list[ReservationResponse])
def list_reservations(db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = db.query(Reservation)
    if user.role.name == "REQUESTER": query = query.filter(Reservation.requester_id == user.id)
    return query.order_by(Reservation.start_date).all()


@router.post("", response_model=ReservationResponse, status_code=201)
def create_reservation(data: ReservationCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "REQUESTER"))):
    if data.end_date <= data.start_date: raise HTTPException(400, "El rango de fechas no es válido")
    resource = db.get(Resource, data.resource_id)
    if not resource: raise HTTPException(404, "Recurso no encontrado")
    if resource.status != "DISPONIBLE": raise HTTPException(409, "El recurso ya no está disponible")
    resource.status = "EN_ESPERA"; resource.version += 1
    reservation = Reservation(**data.model_dump(), requester_id=user.id)
    db.add(reservation); db.flush(); record(db, "CREATE", "reservations", reservation.id, user.id)
    admin = db.query(User).join(User.role).filter_by(name="ADMIN").first()
    if admin: queue_notification(db, admin, "Nueva reserva", f"Reserva #{reservation.id} pendiente")
    db.commit(); return reservation


@router.patch("/{reservation_id}", response_model=ReservationResponse)
def decide(reservation_id: int, data: ReservationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN"))):
    reservation = db.get(Reservation, reservation_id)
    if not reservation: raise HTTPException(404, "Reserva no encontrada")
    reservation.status = data.status; reservation.approved_by = user.id
    record(db, "UPDATE", "reservations", reservation.id, user.id); db.commit(); return reservation
