import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import apply_warehouse_scope, assert_warehouse_access, assigned_warehouse_ids, require_roles
from app.database.connection import get_db
from app.models.purchase_order import PurchaseOrder
from app.models.user import User, UserRole
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderOut, PurchaseOrderReceive
from app.services.purchase_order_service import (
    approve_purchase_order,
    create_purchase_order,
    receive_purchase_order,
    submit_purchase_order,
)

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"])

PROCUREMENT_ROLES = (UserRole.ADMIN, UserRole.PROCUREMENT_MANAGER)
RECEIVING_ROLES = (UserRole.ADMIN, UserRole.PROCUREMENT_MANAGER, UserRole.WAREHOUSE_MANAGER)


@router.get("", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*RECEIVING_ROLES)),
):
    query = db.query(PurchaseOrder)
    query = apply_warehouse_scope(query, PurchaseOrder.warehouse_id, assigned_warehouse_ids(current_user, db))
    return query.order_by(PurchaseOrder.created_at.desc()).all()


@router.post("", response_model=PurchaseOrderOut)
def create(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*PROCUREMENT_ROLES)),
):
    assert_warehouse_access(current_user, payload.warehouse_id, db)
    return create_purchase_order(
        db,
        supplier_id=payload.supplier_id,
        warehouse_id=payload.warehouse_id,
        items=[item.model_dump() for item in payload.items],
        created_by_id=current_user.id,
        expected_delivery_date=payload.expected_delivery_date,
        notes=payload.notes,
    )


@router.get("/{purchase_order_id}", response_model=PurchaseOrderOut)
def get_purchase_order(
    purchase_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*RECEIVING_ROLES)),
):
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == purchase_order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    assert_warehouse_access(current_user, order.warehouse_id, db)
    return order


@router.post("/{purchase_order_id}/submit", response_model=PurchaseOrderOut)
def submit(
    purchase_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*PROCUREMENT_ROLES)),
):
    return submit_purchase_order(db, purchase_order_id)


@router.post("/{purchase_order_id}/approve", response_model=PurchaseOrderOut)
def approve(
    purchase_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*PROCUREMENT_ROLES)),
):
    return approve_purchase_order(db, purchase_order_id)


@router.post("/{purchase_order_id}/receive", response_model=PurchaseOrderOut)
def receive(
    purchase_order_id: uuid.UUID,
    payload: PurchaseOrderReceive,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*RECEIVING_ROLES)),
):
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == purchase_order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    assert_warehouse_access(current_user, order.warehouse_id, db)
    return receive_purchase_order(
        db,
        purchase_order_id=purchase_order_id,
        receipts=[r.model_dump() for r in payload.receipts],
        received_by_id=current_user.id,
    )
