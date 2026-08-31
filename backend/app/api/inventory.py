import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import apply_warehouse_scope, assert_warehouse_access, assigned_warehouse_ids, require_roles
from app.database.connection import get_db
from app.models.inventory import Inventory
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User, UserRole
from app.schemas.inventory import InventoryOut, StockAdjustment, StockMovementOut
from app.services.auth_service import get_current_user
from app.services.inventory_service import apply_stock_movement, get_low_stock_products

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _inventory_out(inv: Inventory) -> InventoryOut:
    product = inv.product
    warehouse = inv.warehouse
    return InventoryOut(
        id=inv.id,
        product_id=inv.product_id,
        warehouse_id=inv.warehouse_id,
        quantity_on_hand=inv.quantity_on_hand,
        quantity_reserved=inv.quantity_reserved,
        product_name=product.name if product else None,
        product_sku=product.sku if product else None,
        reorder_level=product.reorder_level if product else 0,
        warehouse_name=warehouse.name if warehouse else None,
    )


@router.get("", response_model=list[InventoryOut])
def list_inventory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    warehouse_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
):
    if warehouse_id:
        assert_warehouse_access(current_user, warehouse_id, db)
    query = db.query(Inventory).options(joinedload(Inventory.product), joinedload(Inventory.warehouse))
    query = apply_warehouse_scope(query, Inventory.warehouse_id, assigned_warehouse_ids(current_user, db))
    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    if product_id:
        query = query.filter(Inventory.product_id == product_id)
    return [_inventory_out(row) for row in query.all()]


@router.get("/low-stock", response_model=list[InventoryOut])
def low_stock(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    warehouse_id: uuid.UUID | None = None,
):
    if warehouse_id:
        assert_warehouse_access(current_user, warehouse_id, db)
    rows = get_low_stock_products(db, warehouse_id=warehouse_id)
    scoped = assigned_warehouse_ids(current_user, db)
    if scoped is not None:
        allowed = set(scoped)
        rows = [row for row in rows if row.warehouse_id in allowed]
    return [_inventory_out(row) for row in rows]


@router.get("/movements", response_model=list[StockMovementOut])
def list_movements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    movement_type: MovementType | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    query = db.query(StockMovement)
    query = apply_warehouse_scope(query, StockMovement.warehouse_id, assigned_warehouse_ids(current_user, db))
    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    if warehouse_id:
        query = query.filter(StockMovement.warehouse_id == warehouse_id)
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)
    return query.order_by(StockMovement.created_at.desc()).limit(limit).all()


@router.post("/adjust", response_model=StockMovementOut)
def adjust_stock(
    payload: StockAdjustment,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_MANAGER)
    ),
):
    if payload.quantity_delta == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity cannot be zero")
    assert_warehouse_access(current_user, payload.warehouse_id, db)
    movement_type = (
        MovementType.ADJUSTMENT_IN if payload.quantity_delta > 0 else MovementType.ADJUSTMENT_OUT
    )
    return apply_stock_movement(
        db,
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        movement_type=movement_type,
        quantity=payload.quantity_delta,
        created_by_id=current_user.id,
        reason=payload.reason,
    )
