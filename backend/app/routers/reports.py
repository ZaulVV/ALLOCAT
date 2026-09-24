from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Reservation, Resource, User
from ..security import require_roles

router = APIRouter()


@router.get("/metrics")
def metrics(db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "AUDITOR"))):
    total = db.query(Reservation).count()
    approved = db.query(Reservation).filter_by(status="APROBADA").count()
    demanded = db.query(Reservation.resource_id, Resource.name).join(Resource).group_by(Reservation.resource_id, Resource.name).order_by(func.count(Reservation.id).desc()).first()
    return {"total_reservations": total, "utilization_rate": round(approved / total, 4) if total else 0, "most_demanded_resource": demanded.name if demanded else None}


@router.get("/pdf")
def pdf(db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "AUDITOR"))):
    output = BytesIO(); doc = canvas.Canvas(output)
    doc.drawString(72, 780, "ALLOCAT - Reporte de reservas")
    doc.drawString(72, 760, f"Total de reservas: {db.query(Reservation).count()}")
    doc.save(); output.seek(0)
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=allocat-report.pdf"})
