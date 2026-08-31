import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.customer_order import Customer, CustomerOrderStatus
from app.models.inventory import Inventory
from app.models.product import Product, ProductStatus
from app.models.stock_movement import MovementType
from app.services.inventory_service import apply_stock_movement
from app.services.order_service import cancel_order, confirm_order, create_customer_order, fulfill_order
from tests.conftest import make_user, make_warehouse


def make_product(db):
    product = Product(
        sku=f"SKU-{uuid.uuid4().hex[:8]}", name="Order Test Product",
        unit_price=Decimal("20.00"), cost_price=Decimal("10.00"),
        reorder_level=5, reorder_quantity=50, status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def make_customer(db):
    customer = Customer(name="Test Customer")
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def test_confirm_reserves_stock(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    product = make_product(db)
    customer = make_customer(db)

    apply_stock_movement(
        db, product_id=product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=50, created_by_id=user.id, reason="opening",
    )

    order = create_customer_order(
        db, customer_id=customer.id, warehouse_id=warehouse.id,
        items=[{"product_id": product.id, "quantity": 10, "unit_price": Decimal("20.00")}],
        created_by_id=user.id,
    )
    confirm_order(db, order.id)

    inv = db.query(Inventory).filter(Inventory.product_id == product.id).first()
    assert inv.quantity_reserved == 10
    assert inv.quantity_on_hand == 50  # unchanged until fulfillment


def test_cannot_confirm_order_exceeding_available_stock(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    product = make_product(db)
    customer = make_customer(db)

    apply_stock_movement(
        db, product_id=product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=5, created_by_id=user.id, reason="opening",
    )

    order = create_customer_order(
        db, customer_id=customer.id, warehouse_id=warehouse.id,
        items=[{"product_id": product.id, "quantity": 10, "unit_price": Decimal("20.00")}],
        created_by_id=user.id,
    )
    with pytest.raises(HTTPException) as exc_info:
        confirm_order(db, order.id)
    assert exc_info.value.status_code == 409


def test_fulfill_order_deducts_on_hand_and_reservation(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    product = make_product(db)
    customer = make_customer(db)

    apply_stock_movement(
        db, product_id=product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=50, created_by_id=user.id, reason="opening",
    )
    order = create_customer_order(
        db, customer_id=customer.id, warehouse_id=warehouse.id,
        items=[{"product_id": product.id, "quantity": 10, "unit_price": Decimal("20.00")}],
        created_by_id=user.id,
    )
    confirm_order(db, order.id)
    fulfilled = fulfill_order(db, order.id, fulfilled_by_id=user.id)

    assert fulfilled.status == CustomerOrderStatus.FULFILLED
    inv = db.query(Inventory).filter(Inventory.product_id == product.id).first()
    assert inv.quantity_on_hand == 40
    assert inv.quantity_reserved == 0


def test_cancel_releases_reservation(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    product = make_product(db)
    customer = make_customer(db)

    apply_stock_movement(
        db, product_id=product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=50, created_by_id=user.id, reason="opening",
    )
    order = create_customer_order(
        db, customer_id=customer.id, warehouse_id=warehouse.id,
        items=[{"product_id": product.id, "quantity": 10, "unit_price": Decimal("20.00")}],
        created_by_id=user.id,
    )
    confirm_order(db, order.id)
    cancel_order(db, order.id)

    inv = db.query(Inventory).filter(Inventory.product_id == product.id).first()
    assert inv.quantity_reserved == 0
    assert inv.quantity_on_hand == 50
