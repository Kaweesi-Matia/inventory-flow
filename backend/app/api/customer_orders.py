import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import apply_warehouse_scope, assert_warehouse_access, assigned_warehouse_ids, require_roles
from app.database.connection import get_db
from app.models.customer_order import Customer, CustomerOrder
from app.models.user import User, UserRole
from app.schemas.customer_order import (
    CustomerCreate,
    CustomerOrderCreate,
    CustomerOrderOut,
    CustomerOut,
)
from app.services.order_service import cancel_order, confirm_order, create_customer_order, fulfill_order

router = APIRouter(prefix="/api/orders", tags=["customer-orders"])
customers_router = APIRouter(prefix="/api/customers", tags=["customers"])

SALES_ROLES = (UserRole.ADMIN, UserRole.SALES_USER)
FULFILL_ROLES = (UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER)
ORDER_VIEW_ROLES = (UserRole.ADMIN, UserRole.SALES_USER, UserRole.WAREHOUSE_MANAGER)


@customers_router.get("", response_model=list[CustomerOut])
def list_customers(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*ORDER_VIEW_ROLES)),
):
    return db.query(Customer).order_by(Customer.name).all()


@customers_router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*SALES_ROLES)),
):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerOrderOut])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ORDER_VIEW_ROLES)),
):
    query = db.query(CustomerOrder)
    query = apply_warehouse_scope(query, CustomerOrder.warehouse_id, assigned_warehouse_ids(current_user, db))
    return query.order_by(CustomerOrder.created_at.desc()).all()


@router.post("", response_model=CustomerOrderOut)
def create(
    payload: CustomerOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    assert_warehouse_access(current_user, payload.warehouse_id, db)
    return create_customer_order(
        db,
        customer_id=payload.customer_id,
        warehouse_id=payload.warehouse_id,
        items=[item.model_dump() for item in payload.items],
        created_by_id=current_user.id,
    )


@router.get("/{order_id}", response_model=CustomerOrderOut)
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ORDER_VIEW_ROLES)),
):
    order = db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    assert_warehouse_access(current_user, order.warehouse_id, db)
    return order


@router.post("/{order_id}/confirm", response_model=CustomerOrderOut)
def confirm(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    order = db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    assert_warehouse_access(current_user, order.warehouse_id, db)
    return confirm_order(db, order_id)


@router.post("/{order_id}/fulfill", response_model=CustomerOrderOut)
def fulfill(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*FULFILL_ROLES)),
):
    order = db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    assert_warehouse_access(current_user, order.warehouse_id, db)
    return fulfill_order(db, order_id, fulfilled_by_id=current_user.id)


@router.post("/{order_id}/cancel", response_model=CustomerOrderOut)
def cancel(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    order = db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    assert_warehouse_access(current_user, order.warehouse_id, db)
    return cancel_order(db, order_id)
