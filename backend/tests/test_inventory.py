import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.product import Product, ProductStatus
from app.services.inventory_service import (
    apply_stock_movement,
    consume_reservation,
    get_low_stock_products,
    release_reservation,
    reserve_stock,
)
from app.models.stock_movement import MovementType
from tests.conftest import make_user, make_warehouse


def make_product(db, reorder_level=10):
    product = Product(
        sku=f"SKU-{uuid.uuid4().hex[:8]}",
        name="Test Product",
        unit_price=Decimal("10.00"),
        cost_price=Decimal("5.00"),
        reorder_level=reorder_level,
        reorder_quantity=50,
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def test_apply_stock_movement_increases_on_hand(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    product = make_product(db)

    movement = apply_stock_movement(
        db, product_id=product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=50, created_by_id=user.id, reason="test",
    )
    assert movement.quantity == 50

    from app.models.inventory import Inventory
    inv = db.query(Inventory).filter(Inventory.product_id == product.id).first()
    assert inv.quantity_on_hand == 50


def test_negative_stock_is_rejected(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    product = make_product(db)

    apply_stock_movement(
        db, product_id=product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=10, created_by_id=user.id, reason="opening",
    )

    with pytest.raises(HTTPException) as exc_info:
        apply_stock_movement(
            db, product_id=product.id, warehouse_id=warehouse.id,
            movement_type=MovementType.ADJUSTMENT_OUT, quantity=-20, created_by_id=user.id, reason="too much",
        )
    assert exc_info.value.status_code == 409


def test_reserve_stock_cannot_exceed_available(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    product = make_product(db)
    apply_stock_movement(
        db, product_id=product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=30, created_by_id=user.id, reason="opening",
    )

    reserve_stock(db, product_id=product.id, warehouse_id=warehouse.id, quantity=30)

    with pytest.raises(HTTPException) as exc_info:
        reserve_stock(db, product_id=product.id, warehouse_id=warehouse.id, quantity=1)
    assert exc_info.value.status_code == 409


def test_release_reservation_frees_available_stock(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    product = make_product(db)
    apply_stock_movement(
        db, product_id=product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=30, created_by_id=user.id, reason="opening",
    )
    reserve_stock(db, product_id=product.id, warehouse_id=warehouse.id, quantity=20)
    release_reservation(db, product_id=product.id, warehouse_id=warehouse.id, quantity=20)

    from app.models.inventory import Inventory
    inv = db.query(Inventory).filter(Inventory.product_id == product.id).first()
    assert inv.quantity_reserved == 0
    assert inv.quantity_on_hand == 30


def test_consume_reservation_reduces_on_hand_and_reserved(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    product = make_product(db)
    apply_stock_movement(
        db, product_id=product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=30, created_by_id=user.id, reason="opening",
    )
    reserve_stock(db, product_id=product.id, warehouse_id=warehouse.id, quantity=15)
    consume_reservation(db, product_id=product.id, warehouse_id=warehouse.id, quantity=15, created_by_id=user.id)

    from app.models.inventory import Inventory
    inv = db.query(Inventory).filter(Inventory.product_id == product.id).first()
    assert inv.quantity_reserved == 0
    assert inv.quantity_on_hand == 15


def test_low_stock_detection(db):
    user = make_user(db)
    warehouse = make_warehouse(db)
    low_product = make_product(db, reorder_level=20)
    healthy_product = make_product(db, reorder_level=5)

    apply_stock_movement(
        db, product_id=low_product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=10, created_by_id=user.id, reason="low",
    )
    apply_stock_movement(
        db, product_id=healthy_product.id, warehouse_id=warehouse.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=100, created_by_id=user.id, reason="healthy",
    )

    low_stock_rows = get_low_stock_products(db, warehouse_id=warehouse.id)
    low_stock_product_ids = {row.product_id for row in low_stock_rows}
    assert low_product.id in low_stock_product_ids
    assert healthy_product.id not in low_stock_product_ids
