import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.customer_order import CustomerOrder, CustomerOrderItem, CustomerOrderStatus
from app.services.inventory_service import consume_reservation, release_reservation, reserve_stock


def _generate_order_number(db: Session) -> str:
    count = db.query(CustomerOrder).count()
    return f"SO-{1000 + count + 1}"


def create_customer_order(
    db: Session,
    *,
    customer_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    items: list[dict],
    created_by_id: uuid.UUID,
) -> CustomerOrder:
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An order needs at least one item")

    order = CustomerOrder(
        order_number=_generate_order_number(db),
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        order_date=date.today(),
        status=CustomerOrderStatus.PENDING,
        created_by_id=created_by_id,
        total_amount=0,
    )
    db.add(order)
    db.flush()

    total = 0
    for item in items:
        if item["quantity"] <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order quantity must be positive")
        db.add(
            CustomerOrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
            )
        )
        total += item["quantity"] * item["unit_price"]

    order.total_amount = total
    db.commit()
    db.refresh(order)
    return order


def confirm_order(db: Session, order_id: uuid.UUID) -> CustomerOrder:
    """
    Moves PENDING -> CONFIRMED and reserves stock for every line item.
    If any line can't be reserved (insufficient available stock), the
    whole confirmation is rolled back so the order stays PENDING with no
    partial reservations left dangling.
    """
    order = (
        db.query(CustomerOrder)
        .filter(CustomerOrder.id == order_id)
        .with_for_update()
        .first()
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != CustomerOrderStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a PENDING order can be confirmed")

    try:
        for item in order.items:
            reserve_stock(
                db,
                product_id=item.product_id,
                warehouse_id=order.warehouse_id,
                quantity=item.quantity,
                commit=False,
            )
        order.status = CustomerOrderStatus.RESERVED
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    return order


def fulfill_order(db: Session, order_id: uuid.UUID, fulfilled_by_id: uuid.UUID) -> CustomerOrder:
    order = (
        db.query(CustomerOrder)
        .filter(CustomerOrder.id == order_id)
        .with_for_update()
        .first()
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != CustomerOrderStatus.RESERVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only a RESERVED order can be fulfilled"
        )

    try:
        for item in order.items:
            consume_reservation(
                db,
                product_id=item.product_id,
                warehouse_id=order.warehouse_id,
                quantity=item.quantity,
                created_by_id=fulfilled_by_id,
                reference_number=order.order_number,
                commit=False,
            )
        order.status = CustomerOrderStatus.FULFILLED
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    return order


def cancel_order(db: Session, order_id: uuid.UUID) -> CustomerOrder:
    order = (
        db.query(CustomerOrder)
        .filter(CustomerOrder.id == order_id)
        .with_for_update()
        .first()
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status == CustomerOrderStatus.FULFILLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot cancel a fulfilled order")

    try:
        if order.status == CustomerOrderStatus.RESERVED:
            for item in order.items:
                release_reservation(
                    db,
                    product_id=item.product_id,
                    warehouse_id=order.warehouse_id,
                    quantity=item.quantity,
                    commit=False,
                )
        order.status = CustomerOrderStatus.CANCELLED
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    return order
