import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.product import Product, ProductStatus
from app.models.purchase_order import PurchaseOrderStatus
from app.models.supplier import Supplier, SupplierStatus
from app.services.purchase_order_service import create_purchase_order, receive_purchase_order
from tests.conftest import make_user, make_warehouse


def make_product(db):
    product = Product(
        sku=f"SKU-{uuid.uuid4().hex[:8]}", name="PO Test Product",
        unit_price=Decimal("10.00"), cost_price=Decimal("5.00"),
        reorder_level=5, reorder_quantity=50, status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def make_supplier(db):
    supplier = Supplier(company_name="Test Supplier", status=SupplierStatus.ACTIVE)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def test_create_purchase_order_calculates_total(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    supplier = make_supplier(db)
    product = make_product(db)

    order = create_purchase_order(
        db, supplier_id=supplier.id, warehouse_id=warehouse.id,
        items=[{"product_id": product.id, "quantity": 10, "unit_cost": Decimal("5.00")}],
        created_by_id=user.id,
    )
    assert order.total_cost == Decimal("50.00")
    assert order.status == PurchaseOrderStatus.DRAFT


def test_partial_receiving_updates_status_and_inventory(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    supplier = make_supplier(db)
    product = make_product(db)

    order = create_purchase_order(
        db, supplier_id=supplier.id, warehouse_id=warehouse.id,
        items=[{"product_id": product.id, "quantity": 100, "unit_cost": Decimal("5.00")}],
        created_by_id=user.id,
    )
    item = order.items[0]

    updated = receive_purchase_order(
        db, purchase_order_id=order.id,
        receipts=[{"item_id": item.id, "quantity_received": 60}],
        received_by_id=user.id,
    )
    assert updated.status == PurchaseOrderStatus.PARTIALLY_RECEIVED
    assert updated.items[0].quantity_received == 60

    from app.models.inventory import Inventory
    inv = db.query(Inventory).filter(Inventory.product_id == product.id, Inventory.warehouse_id == warehouse.id).first()
    assert inv.quantity_on_hand == 60

    # Receive the rest.
    fully_updated = receive_purchase_order(
        db, purchase_order_id=order.id,
        receipts=[{"item_id": item.id, "quantity_received": 40}],
        received_by_id=user.id,
    )
    assert fully_updated.status == PurchaseOrderStatus.RECEIVED


def test_cannot_receive_more_than_ordered(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    supplier = make_supplier(db)
    product = make_product(db)

    order = create_purchase_order(
        db, supplier_id=supplier.id, warehouse_id=warehouse.id,
        items=[{"product_id": product.id, "quantity": 10, "unit_cost": Decimal("5.00")}],
        created_by_id=user.id,
    )
    item = order.items[0]

    with pytest.raises(HTTPException) as exc_info:
        receive_purchase_order(
            db, purchase_order_id=order.id,
            receipts=[{"item_id": item.id, "quantity_received": 20}],
            received_by_id=user.id,
        )
    assert exc_info.value.status_code == 409

    # Nothing should have been committed — rollback semantics.
    from app.models.inventory import Inventory
    inv = db.query(Inventory).filter(Inventory.product_id == product.id).first()
    assert inv is None


def test_cannot_receive_against_cancelled_order(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    supplier = make_supplier(db)
    product = make_product(db)

    order = create_purchase_order(
        db, supplier_id=supplier.id, warehouse_id=warehouse.id,
        items=[{"product_id": product.id, "quantity": 10, "unit_cost": Decimal("5.00")}],
        created_by_id=user.id,
    )
    order.status = PurchaseOrderStatus.CANCELLED
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        receive_purchase_order(
            db, purchase_order_id=order.id,
            receipts=[{"item_id": order.items[0].id, "quantity_received": 5}],
            received_by_id=user.id,
        )
    assert exc_info.value.status_code == 409
