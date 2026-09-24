from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..audit import record
from ..database import get_db
from ..models import Resource, User
from ..schemas import ResourceCreate, ResourceResponse, ResourceUpdate
from ..security import current_user, require_roles

router = APIRouter()


@router.get("", response_model=list[ResourceResponse])
def list_resources(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return db.query(Resource).order_by(Resource.id).all()


@router.post("", response_model=ResourceResponse, status_code=201)
def create_resource(data: ResourceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN"))):
    resource = Resource(**data.model_dump())
    db.add(resource); db.flush(); record(db, "CREATE", "resources", resource.id, user.id); db.commit()
    return resource


@router.put("/{resource_id}", response_model=ResourceResponse)
def update_resource(resource_id: int, data: ResourceUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN"))):
    resource = db.get(Resource, resource_id)
    if not resource: raise HTTPException(404, "Recurso no encontrado")
    if resource.version != data.version: raise HTTPException(409, "El recurso fue modificado por otro usuario")
    for key, value in data.model_dump(exclude={"version"}).items(): setattr(resource, key, value)
    resource.version += 1
    record(db, "UPDATE", "resources", resource.id, user.id); db.commit()
    return resource


@router.delete("/{resource_id}", status_code=204)
def delete_resource(resource_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN"))):
    resource = db.get(Resource, resource_id)
    if not resource: raise HTTPException(404, "Recurso no encontrado")
    db.delete(resource); record(db, "DELETE", "resources", resource.id, user.id); db.commit()
