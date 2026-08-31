"""
All inventory mutations funnel through this module. Nothing outside this
service should ever write to `inventory.quantity_on_hand` or
`quantity_reserved` directly — that's what keeps the stock_movements
ledger authoritative and prevents the two from drifting apart.

Concurrency strategy
---------------------
Two (or more) requests can try to adjust the same product/warehouse row
at the same time — e.g. two sales reserving the last units, or a
transfer racing an adjustment. We use `SELECT ... FOR UPDATE` (via
SQLAlchemy's `with_for_update()`) to take a row-level lock on the
`inventory` row before reading its current quantity. The second
transaction blocks until the first commits or rolls back, then sees the
up-to-date value — so "check available, then deduct" can never race.
The DB CHECK constraints (`quantity_on_hand >= 0`, `reserved <= on_hand`)
are a second, unconditional line of defense in case any code path here
has a bug.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, contains_eager

from app.models.inventory import Inventory
from app.models.stock_movement import MovementType, StockMovement


def _get_or_create_locked_inventory_row(
    db: Session, product_id: uuid.UUID, warehouse_id: uuid.UUID
) -> Inventory:
    """
    Fetch the inventory row for (product, warehouse) with a row lock,
    creating it with zero quantities first if it doesn't exist yet.
    Must be called inside an open transaction.
    """
    inventory = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id, Inventory.warehouse_id == warehouse_id)
        .with_for_update()
        .first()
    )
    if inventory is None:
        inventory = Inventory(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity_on_hand=0,
            quantity_reserved=0,
        )
        db.add(inventory)
        db.flush()  # get it into the transaction / assign defaults before re-locking
        inventory = (
            db.query(Inventory)
            .filter(Inventory.id == inventory.id)
            .with_for_update()
            .first()
        )
    return inventory


def apply_stock_movement(
    db: Session,
    *,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    movement_type: MovementType,
    quantity: int,
    created_by_id: uuid.UUID,
    reference_number: str | None = None,
    reason: str | None = None,
    commit: bool = True,
) -> StockMovement:
    """
    Apply a signed quantity change to quantity_on_hand and write the
    corresponding ledger row, atomically.

    `quantity` must be signed: positive increases on_hand (receipts,
    transfer-in, adjustment-in, returns), negative decreases it (sales,
    transfer-out, adjustment-out, damage, loss).

    Raises 409 if the movement would drive on_hand negative.
    Does NOT touch quantity_reserved — see reserve_stock /
    release_reservation / consume_reservation for reservation handling.
    """
    if quantity == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity cannot be zero")

    inventory = _get_or_create_locked_inventory_row(db, product_id, warehouse_id)

    new_on_hand = inventory.quantity_on_hand + quantity
    if new_on_hand < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Insufficient stock: on hand {inventory.quantity_on_hand}, "
                f"attempted change {quantity}"
            ),
        )
    if new_on_hand < inventory.quantity_reserved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This movement would drop on-hand stock below already-reserved quantity",
        )

    inventory.quantity_on_hand = new_on_hand

    movement = StockMovement(
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        quantity=quantity,
        reference_number=reference_number,
        reason=reason,
        created_by_id=created_by_id,
    )
    db.add(movement)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock movement violates a database integrity constraint",
        )

    if commit:
        db.commit()
        db.refresh(movement)
    return movement


def reserve_stock(
    db: Session, *, product_id: uuid.UUID, warehouse_id: uuid.UUID, quantity: int, commit: bool = True
) -> Inventory:
    """
    Reserve `quantity` units against available stock (on_hand - reserved).
    Used when a customer order moves to CONFIRMED/RESERVED. Raises 409 if
    insufficient available stock.
    """
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be positive")

    inventory = _get_or_create_locked_inventory_row(db, product_id, warehouse_id)
    available = inventory.quantity_on_hand - inventory.quantity_reserved
    if quantity > available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reserve {quantity} units — only {available} available",
        )

    inventory.quantity_reserved += quantity
    db.flush()
    if commit:
        db.commit()
        db.refresh(inventory)
    return inventory


def release_reservation(
    db: Session, *, product_id: uuid.UUID, warehouse_id: uuid.UUID, quantity: int, commit: bool = True
) -> Inventory:
    """Release a previously-made reservation without touching on_hand (order cancelled)."""
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be positive")

    inventory = _get_or_create_locked_inventory_row(db, product_id, warehouse_id)
    inventory.quantity_reserved = max(0, inventory.quantity_reserved - quantity)
    db.flush()
    if commit:
        db.commit()
        db.refresh(inventory)
    return inventory


def consume_reservation(
    db: Session,
    *,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: int,
    created_by_id: uuid.UUID,
    reference_number: str | None = None,
    commit: bool = True,
) -> StockMovement:
    """
    Convert a reservation into a completed reduction: releases the
    reservation AND deducts on_hand AND writes a SALE movement, all under
    the same row lock. Used on order fulfillment.
    """
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be positive")

    inventory = _get_or_create_locked_inventory_row(db, product_id, warehouse_id)
    if quantity > inventory.quantity_reserved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot fulfill more than what was reserved for this order",
        )
    if quantity > inventory.quantity_on_hand:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Insufficient on-hand stock to fulfill this order"
        )

    inventory.quantity_reserved -= quantity
    inventory.quantity_on_hand -= quantity

    movement = StockMovement(
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=MovementType.SALE,
        quantity=-quantity,
        reference_number=reference_number,
        reason="Order fulfillment",
        created_by_id=created_by_id,
    )
    db.add(movement)
    db.flush()

    if commit:
        db.commit()
        db.refresh(movement)
    return movement


def get_low_stock_products(db: Session, warehouse_id: uuid.UUID | None = None):
    """
    Returns Inventory rows where available_quantity <= the product's
    reorder_level. Joins to Product for the threshold since reorder_level
    lives on the product, not per-warehouse.
    """
    from app.models.product import Product  # local import avoids circulars

    query = (
        db.query(Inventory)
        .join(Inventory.product)
        .options(contains_eager(Inventory.product), joinedload(Inventory.warehouse))
        .filter((Inventory.quantity_on_hand - Inventory.quantity_reserved) <= Product.reorder_level)
    )
    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    return query.all()
