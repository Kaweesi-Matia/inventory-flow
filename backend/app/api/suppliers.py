import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.database.connection import get_db
from app.models.supplier import Supplier
from app.models.user import User, UserRole
from app.schemas.partner import SupplierCreate, SupplierOut

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


PROCUREMENT_ROLES = (UserRole.ADMIN, UserRole.PROCUREMENT_MANAGER)


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*PROCUREMENT_ROLES)),
    search: str | None = Query(default=None),
):
    query = db.query(Supplier)
    if search:
        query = query.filter(Supplier.company_name.ilike(f"%{search}%"))
    return query.all()


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*PROCUREMENT_ROLES)),
):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles(*PROCUREMENT_ROLES))):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*PROCUREMENT_ROLES)),
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    for field, value in payload.model_dump().items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier
