import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.stock_movement import MovementType
from app.models.transfer import InventoryTransfer, InventoryTransferItem, TransferStatus
from app.services.inventory_service import apply_stock_movement


def _generate_transfer_number(db: Session) -> str:
    count = db.query(InventoryTransfer).count()
    return f"TRF-{1000 + count + 1}"


def create_transfer(
    db: Session,
    *,
    source_warehouse_id: uuid.UUID,
    destination_warehouse_id: uuid.UUID,
    items: list[dict],
    created_by_id: uuid.UUID,
    notes: str | None = None,
) -> InventoryTransfer:
    if source_warehouse_id == destination_warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination warehouse must differ",
        )
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A transfer needs at least one item")

    transfer = InventoryTransfer(
        transfer_number=_generate_transfer_number(db),
        source_warehouse_id=source_warehouse_id,
        destination_warehouse_id=destination_warehouse_id,
        status=TransferStatus.PENDING,
        created_by_id=created_by_id,
        notes=notes,
    )
    db.add(transfer)
    db.flush()

    for item in items:
        if item["quantity"] <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transfer quantity must be positive")
        db.add(
            InventoryTransferItem(
                transfer_id=transfer.id, product_id=item["product_id"], quantity=item["quantity"]
            )
        )

    db.commit()
    db.refresh(transfer)
    return transfer


def receive_transfer(db: Session, *, transfer_id: uuid.UUID, received_by_id: uuid.UUID) -> InventoryTransfer:
    """
    Moves stock out of the source warehouse and into the destination
    warehouse atomically. Both legs (TRANSFER_OUT and TRANSFER_IN) are
    written in the same transaction: if the destination-side write fails
    for any reason, the source-side deduction is rolled back too, so
    stock can never vanish or duplicate.
    """
    transfer = (
        db.query(InventoryTransfer)
        .filter(InventoryTransfer.id == transfer_id)
        .with_for_update()
        .first()
    )
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    if transfer.status in (TransferStatus.RECEIVED, TransferStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot receive a transfer in status {transfer.status.value}",
        )

    try:
        for item in transfer.items:
            apply_stock_movement(
                db,
                product_id=item.product_id,
                warehouse_id=transfer.source_warehouse_id,
                movement_type=MovementType.TRANSFER_OUT,
                quantity=-item.quantity,
                created_by_id=received_by_id,
                reference_number=transfer.transfer_number,
                reason="Warehouse transfer — outbound leg",
                commit=False,
            )
            apply_stock_movement(
                db,
                product_id=item.product_id,
                warehouse_id=transfer.destination_warehouse_id,
                movement_type=MovementType.TRANSFER_IN,
                quantity=item.quantity,
                created_by_id=received_by_id,
                reference_number=transfer.transfer_number,
                reason="Warehouse transfer — inbound leg",
                commit=False,
            )

        transfer.status = TransferStatus.RECEIVED
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(transfer)
    return transfer


def cancel_transfer(db: Session, transfer_id: uuid.UUID) -> InventoryTransfer:
    transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).with_for_update().first()
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    if transfer.status == TransferStatus.RECEIVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot cancel a transfer already received")
    transfer.status = TransferStatus.CANCELLED
    db.commit()
    db.refresh(transfer)
    return transfer
