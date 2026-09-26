"""Siembra datos de prueba para el escaneo con OWASP ZAP.

Crea los roles que el backend ya crea, tres usuarios (uno por rol) y un
recurso + una reserva PENDIENTE. Los ids 1 son intencionales: son los
destinos de PUT /resources/{id}, PATCH /reservations/{id} y
DELETE /resources/{id}, y ZAP necesita que esos endpoints devuelvan algo
distinto de 404 para que el escaneo activo tenga sobre que trabajar.

Es idempotente: si los registros ya existen no los duplica. Es de un solo
uso, se ejecuta con `docker compose --profile tools run --rm seed`.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import Base, SessionLocal, engine  # noqa: E402
from backend.app.models import Reservation, Resource, Role, User  # noqa: E402
from backend.app.security import hash_password  # noqa: E402

ROLES = ("ADMIN", "REQUESTER", "AUDITOR")

DEFAULT_PASSWORD = "ZapAllocat2026!"
# .local / .test / .invalid / .example / .onion son dominios de uso especial y
# email-validator los rechaza, asi que un usuario con esos dominios nunca podria
# hacer login (422 en vez de 401). Usar un dominio normal.
DEFAULT_DOMAIN = "example.com"


def _password(kind: str) -> str:
    return os.getenv(f"ALLOCAT_{kind}_PASSWORD", DEFAULT_PASSWORD)


def _email(kind: str) -> str:
    return os.getenv(f"ALLOCAT_{kind}_EMAIL", f"{kind.lower()}@{DEFAULT_DOMAIN}")


def main() -> int:
    # Si DATABASE_URL no viene del entorno, config.py cae en su default
    # sqlite:///./allocat.db y los datos se pierden al borrar el contenedor.
    # Es un fallo silencioso: el seed "funciona" pero no siembra nada.
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit(
            "DATABASE_URL no esta definida. Sin ella config.py usa el default "
            "sqlite:///./allocat.db y el seed escribe en un archivo descartable "
            "dentro del contenedor. Revisa el bloque `environment` del servicio "
            "seed en docker-compose.yml."
        )
    print(f"Base de datos: {url.split('@')[-1]}")

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        roles: dict[str, Role] = {}
        for name in ROLES:
            role = db.query(Role).filter_by(name=name).first()
            if role is None:
                role = Role(name=name)
                db.add(role)
            roles[name] = role
        db.commit()

        users: dict[str, User] = {}
        for name in ROLES:
            email = _email(name)
            user = db.query(User).filter_by(email=email).first()
            if user is None:
                user = User(
                    name=f"ZAP {name}",
                    email=email,
                    hashed_password=hash_password(_password(name)),
                    role=roles[name],
                    is_active=True,
                )
                db.add(user)
                db.flush()
            users[name] = user
        db.commit()

        resource = db.query(Resource).filter_by(name="Proyector ZAP").first()
        if resource is None:
            resource = Resource(name="Proyector ZAP", category="electronico")
            db.add(resource)
            db.flush()

        reservation = (
            db.query(Reservation)
            .filter_by(resource_id=resource.id, requester_id=users["REQUESTER"].id)
            .first()
        )
        if reservation is None:
            start = datetime.now(timezone.utc).replace(microsecond=0)
            reservation = Reservation(
                resource_id=resource.id,
                requester_id=users["REQUESTER"].id,
                start_date=start,
                end_date=start + timedelta(hours=2),
                status="PENDIENTE",
            )
            db.add(reservation)
            db.flush()
        db.commit()

        print("Seed completado.")
        for name in ROLES:
            print(f"  {name:<10} {_email(name):<28} {_password(name)}")
        print(f"  recurso    id={resource.id} status={resource.status}")
        print(f"  reserva    id={reservation.id} status={reservation.status}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
