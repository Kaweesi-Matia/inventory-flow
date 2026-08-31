import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.inventory import Inventory
from app.models.product import Product, ProductStatus
from app.models.stock_movement import MovementType
from app.services.inventory_service import apply_stock_movement
from app.services.transfer_service import create_transfer, receive_transfer
from tests.conftest import make_user, make_warehouse


def make_product(db):
    product = Product(
        sku=f"SKU-{uuid.uuid4().hex[:8]}", name="Transfer Test Product",
        unit_price=Decimal("10.00"), cost_price=Decimal("5.00"),
        reorder_level=5, reorder_quantity=50, status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def test_successful_transfer_moves_stock_between_warehouses(db):
    user = make_user(db)
    source = make_warehouse(db, code="WH-SRC")
    destination = make_warehouse(db, code="WH-DST")
    product = make_product(db)

    apply_stock_movement(
        db, product_id=product.id, warehouse_id=source.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=100, created_by_id=user.id, reason="opening",
    )

    transfer = create_transfer(
        db, source_warehouse_id=source.id, destination_warehouse_id=destination.id,
        items=[{"product_id": product.id, "quantity": 30}], created_by_id=user.id,
    )
    receive_transfer(db, transfer_id=transfer.id, received_by_id=user.id)

    source_inv = db.query(Inventory).filter(Inventory.product_id == product.id, Inventory.warehouse_id == source.id).first()
    dest_inv = db.query(Inventory).filter(Inventory.product_id == product.id, Inventory.warehouse_id == destination.id).first()
    assert source_inv.quantity_on_hand == 70
    assert dest_inv.quantity_on_hand == 30


def test_transfer_exceeding_available_stock_rolls_back_fully(db):
    user = make_user(db)
    source = make_warehouse(db, code="WH-SRC2")
    destination = make_warehouse(db, code="WH-DST2")
    product_a = make_product(db)
    product_b = make_product(db)

    apply_stock_movement(
        db, product_id=product_a.id, warehouse_id=source.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=10, created_by_id=user.id, reason="opening",
    )
    apply_stock_movement(
        db, product_id=product_b.id, warehouse_id=source.id,
        movement_type=MovementType.ADJUSTMENT_IN, quantity=5, created_by_id=user.id, reason="opening",
    )

    # product_b's requested quantity (50) exceeds what's on hand (5) — the
    # whole transfer (including product_a's otherwise-valid line) must roll back.
    transfer = create_transfer(
        db, source_warehouse_id=source.id, destination_warehouse_id=destination.id,
        items=[
            {"product_id": product_a.id, "quantity": 10},
            {"product_id": product_b.id, "quantity": 50},
        ],
        created_by_id=user.id,
    )

    with pytest.raises(HTTPException):
        receive_transfer(db, transfer_id=transfer.id, received_by_id=user.id)

    source_inv_a = db.query(Inventory).filter(Inventory.product_id == product_a.id, Inventory.warehouse_id == source.id).first()
    assert source_inv_a.quantity_on_hand == 10  # untouched — full rollback, not partial


def test_transfer_requires_different_warehouses(db):
    user = make_user(db)
    warehouse = make_warehouse(db, code="WH-SAME")
    product = make_product(db)

    with pytest.raises(Exception):
        create_transfer(
            db, source_warehouse_id=warehouse.id, destination_warehouse_id=warehouse.id,
            items=[{"product_id": product.id, "quantity": 5}], created_by_id=user.id,
        )
