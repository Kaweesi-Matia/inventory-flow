from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.permissions import apply_warehouse_scope, assigned_warehouse_ids
from app.database.connection import get_db
from app.models.customer_order import CustomerOrder, CustomerOrderStatus
from app.models.inventory import Inventory
from app.models.product import Product, ProductStatus
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.stock_movement import StockMovement
from app.models.user import User
from app.models.warehouse import Warehouse, WarehouseStatus
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wh_ids = assigned_warehouse_ids(current_user, db)

    total_products = db.query(func.count(Product.id)).filter(Product.status == ProductStatus.ACTIVE).scalar()

    units_q = db.query(func.coalesce(func.sum(Inventory.quantity_on_hand), 0))
    units_q = apply_warehouse_scope(units_q, Inventory.warehouse_id, wh_ids)
    total_units = units_q.scalar()

    low_stock_q = (
        db.query(func.count(Inventory.id))
        .join(Product, Inventory.product_id == Product.id)
        .filter((Inventory.quantity_on_hand - Inventory.quantity_reserved) <= Product.reorder_level)
        .filter((Inventory.quantity_on_hand - Inventory.quantity_reserved) > 0)
    )
    low_stock_q = apply_warehouse_scope(low_stock_q, Inventory.warehouse_id, wh_ids)
    low_stock = low_stock_q.scalar()

    out_q = db.query(func.count(Inventory.id)).filter(
        (Inventory.quantity_on_hand - Inventory.quantity_reserved) <= 0
    )
    out_q = apply_warehouse_scope(out_q, Inventory.warehouse_id, wh_ids)
    out_of_stock = out_q.scalar()

    po_q = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.status.in_([PurchaseOrderStatus.SUBMITTED, PurchaseOrderStatus.APPROVED])
    )
    po_q = apply_warehouse_scope(po_q, PurchaseOrder.warehouse_id, wh_ids)
    pending_purchase_orders = po_q.scalar()

    so_q = db.query(func.count(CustomerOrder.id)).filter(
        CustomerOrder.status.in_([CustomerOrderStatus.PENDING, CustomerOrderStatus.CONFIRMED])
    )
    so_q = apply_warehouse_scope(so_q, CustomerOrder.warehouse_id, wh_ids)
    pending_customer_orders = so_q.scalar()

    wh_q = db.query(func.count(Warehouse.id)).filter(Warehouse.status == WarehouseStatus.ACTIVE)
    if wh_ids is not None:
        wh_q = apply_warehouse_scope(wh_q, Warehouse.id, wh_ids)
    active_warehouses = wh_q.scalar()

    value_q = (
        db.query(func.coalesce(func.sum(Inventory.quantity_on_hand * Product.cost_price), 0))
        .join(Product, Inventory.product_id == Product.id)
    )
    value_q = apply_warehouse_scope(value_q, Inventory.warehouse_id, wh_ids)
    inventory_value = value_q.scalar()

    movements_q = db.query(StockMovement)
    movements_q = apply_warehouse_scope(movements_q, StockMovement.warehouse_id, wh_ids)
    recent_movements = movements_q.order_by(StockMovement.created_at.desc()).limit(10).all()

    return {
        "total_products": total_products,
        "total_inventory_units": int(total_units),
        "low_stock_items": low_stock,
        "out_of_stock_items": out_of_stock,
        "pending_purchase_orders": pending_purchase_orders,
        "pending_customer_orders": pending_customer_orders,
        "active_warehouses": active_warehouses,
        "inventory_value": float(inventory_value),
        "recent_movements": [
            {
                "id": str(m.id),
                "product_id": str(m.product_id),
                "warehouse_id": str(m.warehouse_id),
                "movement_type": m.movement_type.value,
                "quantity": m.quantity,
                "created_at": m.created_at.isoformat(),
            }
            for m in recent_movements
        ],
    }
