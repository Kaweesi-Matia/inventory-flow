import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.models.stock_movement import MovementType
from app.services.inventory_service import apply_stock_movement


def _generate_order_number(db: Session) -> str:
    count = db.query(PurchaseOrder).count()
    return f"PO-{1000 + count + 1}"


def create_purchase_order(
    db: Session,
    *,
    supplier_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    items: list[dict],
    created_by_id: uuid.UUID,
    expected_delivery_date: date | None = None,
    notes: str | None = None,
) -> PurchaseOrder:
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A purchase order needs at least one item")

    order = PurchaseOrder(
        order_number=_generate_order_number(db),
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
        order_date=date.today(),
        expected_delivery_date=expected_delivery_date,
        status=PurchaseOrderStatus.DRAFT,
        notes=notes,
        created_by_id=created_by_id,
        total_cost=0,
    )
    db.add(order)
    db.flush()

    total = 0
    for item in items:
        qty = item["quantity"]
        unit_cost = item["unit_cost"]
        if qty <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item quantity must be positive")
        po_item = PurchaseOrderItem(
            purchase_order_id=order.id,
            product_id=item["product_id"],
            quantity_ordered=qty,
            unit_cost=unit_cost,
        )
        db.add(po_item)
        total += qty * unit_cost

    order.total_cost = total
    db.commit()
    db.refresh(order)
    return order


def receive_purchase_order(
    db: Session,
    *,
    purchase_order_id: uuid.UUID,
    receipts: list[dict],  # [{"item_id": ..., "quantity_received": ...}]
    received_by_id: uuid.UUID,
) -> PurchaseOrder:
    """
    Receive some or all outstanding quantity on a PO, inside a single DB
    transaction:
      1. lock + validate the PO and its items
      2. for each receipt line: increase inventory (PURCHASE_RECEIPT
         movement) and bump quantity_received on the item
      3. recompute PO status (PARTIALLY_RECEIVED vs RECEIVED)
      4. commit — or roll back everything if any line fails validation
    """
    order = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.id == purchase_order_id)
        .with_for_update()
        .first()
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    if order.status in (PurchaseOrderStatus.CANCELLED, PurchaseOrderStatus.RECEIVED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot receive against a purchase order in status {order.status.value}",
        )

    items_by_id = {str(item.id): item for item in order.items}

    try:
        for receipt in receipts:
            item = items_by_id.get(str(receipt["item_id"]))
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Purchase order item {receipt['item_id']} not found on this order",
                )
            qty = receipt["quantity_received"]
            if qty <= 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Received quantity must be positive")
            if item.quantity_received + qty > item.quantity_ordered:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot receive {qty} units for product {item.product_id}: "
                        f"only {item.quantity_ordered - item.quantity_received} remaining"
                    ),
                )

            # Inventory update + ledger entry, same transaction, not yet committed.
            apply_stock_movement(
                db,
                product_id=item.product_id,
                warehouse_id=order.warehouse_id,
                movement_type=MovementType.PURCHASE_RECEIPT,
                quantity=qty,
                created_by_id=received_by_id,
                reference_number=order.order_number,
                reason="Purchase order receipt",
                commit=False,
            )
            item.quantity_received += qty

        # Recompute overall order status from item totals.
        all_items = list(items_by_id.values())
        fully_received = all(i.quantity_received >= i.quantity_ordered for i in all_items)
        any_received = any(i.quantity_received > 0 for i in all_items)
        if fully_received:
            order.status = PurchaseOrderStatus.RECEIVED
        elif any_received:
            order.status = PurchaseOrderStatus.PARTIALLY_RECEIVED

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    return order


def submit_purchase_order(db: Session, purchase_order_id: uuid.UUID) -> PurchaseOrder:
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == purchase_order_id).with_for_update().first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    if order.status != PurchaseOrderStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a DRAFT purchase order can be submitted",
        )
    order.status = PurchaseOrderStatus.SUBMITTED
    db.commit()
    db.refresh(order)
    return order


def approve_purchase_order(db: Session, purchase_order_id: uuid.UUID) -> PurchaseOrder:
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == purchase_order_id).with_for_update().first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    if order.status != PurchaseOrderStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a SUBMITTED purchase order can be approved",
        )
    order.status = PurchaseOrderStatus.APPROVED
    db.commit()
    db.refresh(order)
    return order
