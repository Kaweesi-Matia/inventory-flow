import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.permissions import apply_warehouse_scope, assert_warehouse_access, assigned_warehouse_ids, require_roles
from app.database.connection import get_db
from app.models.transfer import InventoryTransfer
from app.models.user import User, UserRole
from app.schemas.transfer import TransferCreate, TransferOut
from app.services.transfer_service import cancel_transfer, create_transfer, receive_transfer

router = APIRouter(prefix="/api/transfers", tags=["transfers"])

MANAGE_ROLES = (UserRole.ADMIN, UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_MANAGER)


@router.get("", response_model=list[TransferOut])
def list_transfers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
):
    query = db.query(InventoryTransfer)
    wh_ids = assigned_warehouse_ids(current_user, db)
    if wh_ids is not None:
        if not wh_ids:
            query = apply_warehouse_scope(query, InventoryTransfer.source_warehouse_id, wh_ids)
        else:
            query = query.filter(
                or_(
                    InventoryTransfer.source_warehouse_id.in_(wh_ids),
                    InventoryTransfer.destination_warehouse_id.in_(wh_ids),
                )
            )
    return query.order_by(InventoryTransfer.created_at.desc()).all()


@router.post("", response_model=TransferOut)
def create(
    payload: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
):
    assert_warehouse_access(current_user, payload.source_warehouse_id, db)
    return create_transfer(
        db,
        source_warehouse_id=payload.source_warehouse_id,
        destination_warehouse_id=payload.destination_warehouse_id,
        items=[item.model_dump() for item in payload.items],
        created_by_id=current_user.id,
        notes=payload.notes,
    )


@router.get("/{transfer_id}", response_model=TransferOut)
def get_transfer(
    transfer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
):
    transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    scoped = assigned_warehouse_ids(current_user, db)
    if scoped is not None and transfer.source_warehouse_id not in scoped and transfer.destination_warehouse_id not in scoped:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to access this warehouse")
    return transfer


@router.post("/{transfer_id}/receive", response_model=TransferOut)
def receive(
    transfer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
):
    transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    assert_warehouse_access(current_user, transfer.destination_warehouse_id, db)
    return receive_transfer(db, transfer_id=transfer_id, received_by_id=current_user.id)


@router.post("/{transfer_id}/cancel", response_model=TransferOut)
def cancel(
    transfer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
):
    transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    assert_warehouse_access(current_user, transfer.source_warehouse_id, db)
    return cancel_transfer(db, transfer_id)
