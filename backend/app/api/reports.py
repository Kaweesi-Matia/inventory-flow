import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.permissions import apply_warehouse_scope, assigned_warehouse_ids
from app.database.connection import get_db
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.user import User
from app.models.warehouse import Warehouse
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/inventory")
def inventory_valuation(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """SUM(quantity_on_hand * cost_price) per product — done in SQL, not Python."""
    query = (
        db.query(
            Product.id,
            Product.sku,
            Product.name,
            func.sum(Inventory.quantity_on_hand).label("total_on_hand"),
            (func.sum(Inventory.quantity_on_hand) * Product.cost_price).label("total_value"),
        )
        .join(Inventory, Inventory.product_id == Product.id)
    )
    query = apply_warehouse_scope(query, Inventory.warehouse_id, assigned_warehouse_ids(current_user, db))
    rows = query.group_by(Product.id, Product.sku, Product.name, Product.cost_price).all()
    return [
        {
            "product_id": str(r.id),
            "sku": r.sku,
            "name": r.name,
            "total_on_hand": int(r.total_on_hand),
            "total_value": float(r.total_value),
        }
        for r in rows
    ]


@router.get("/warehouse")
def warehouse_inventory(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = (
        db.query(
            Warehouse.id,
            Warehouse.name,
            func.coalesce(func.sum(Inventory.quantity_on_hand), 0).label("total_units"),
        )
        .outerjoin(Inventory, Inventory.warehouse_id == Warehouse.id)
    )
    query = apply_warehouse_scope(query, Warehouse.id, assigned_warehouse_ids(current_user, db))
    rows = query.group_by(Warehouse.id, Warehouse.name).all()
    return [{"warehouse_id": str(r.id), "warehouse_name": r.name, "total_units": int(r.total_units)} for r in rows]


@router.get("/stock-movements")
def stock_movement_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
):
    query = db.query(
        StockMovement.movement_type,
        func.sum(StockMovement.quantity).label("net_quantity"),
        func.count(StockMovement.id).label("movement_count"),
    )
    query = apply_warehouse_scope(query, StockMovement.warehouse_id, assigned_warehouse_ids(current_user, db))
    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    if warehouse_id:
        query = query.filter(StockMovement.warehouse_id == warehouse_id)
    rows = query.group_by(StockMovement.movement_type).all()
    return [
        {"movement_type": r.movement_type.value, "net_quantity": int(r.net_quantity), "count": r.movement_count}
        for r in rows
    ]
