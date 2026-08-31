import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.database.connection import get_db
from app.models.warehouse import Warehouse
from app.models.user import User, UserRole
from app.schemas.partner import WarehouseCreate, WarehouseOut
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/warehouses", tags=["warehouses"])


@router.get("", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(Warehouse).all()


@router.post("", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN)),
):
    existing = db.query(Warehouse).filter(Warehouse.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A warehouse with this code already exists")
    warehouse = Warehouse(**payload.model_dump())
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.get("/{warehouse_id}", response_model=WarehouseOut)
def get_warehouse(warehouse_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(
    warehouse_id: uuid.UUID,
    payload: WarehouseCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN)),
):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    for field, value in payload.model_dump().items():
        setattr(warehouse, field, value)
    db.commit()
    db.refresh(warehouse)
    return warehouse
