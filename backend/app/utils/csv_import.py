"""
Bulk product/inventory CSV import.

Expected columns: sku,name,category,warehouse,quantity,cost_price,reorder_level

This module is pure application-level processing (pandas for parsing +
validation); the actual inventory mutation still goes through
inventory_service.apply_stock_movement so it gets the same transaction
and row-locking guarantees as every other stock change.
"""
import io
import uuid
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product, ProductStatus
from app.models.stock_movement import MovementType
from app.models.warehouse import Warehouse
from app.services.inventory_service import apply_stock_movement

REQUIRED_COLUMNS = {"sku", "name", "category", "warehouse", "quantity", "cost_price", "reorder_level"}


def import_products_csv(db: Session, file_bytes: bytes, imported_by_id: uuid.UUID) -> dict:
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:
        return {"total_rows": 0, "successful": 0, "failed": 0, "duplicates": 0, "errors": [f"Could not parse CSV: {exc}"]}

    missing_columns = REQUIRED_COLUMNS - set(df.columns.str.lower())
    if missing_columns:
        return {
            "total_rows": len(df), "successful": 0, "failed": len(df), "duplicates": 0,
            "errors": [f"Missing required columns: {sorted(missing_columns)}"],
        }

    df.columns = df.columns.str.lower()

    total_rows = len(df)
    successful = 0
    failed = 0
    duplicates = 0
    errors: list[str] = []
    seen_skus: set[str] = set()

    warehouse_cache = {w.code: w for w in db.query(Warehouse).all()}
    category_cache = {c.name: c for c in db.query(Category).all()}

    for idx, row in df.iterrows():
        line_no = idx + 2  # header is line 1
        sku = str(row.get("sku", "")).strip()
        name = str(row.get("name", "")).strip()
        category_name = str(row.get("category", "")).strip()
        warehouse_code = str(row.get("warehouse", "")).strip()

        if not sku or not name:
            failed += 1
            errors.append(f"Row {line_no}: sku and name are required")
            continue

        if sku in seen_skus:
            duplicates += 1
            errors.append(f"Row {line_no}: duplicate SKU '{sku}' within this file")
            continue
        seen_skus.add(sku)

        try:
            quantity = int(row["quantity"])
            cost_price = Decimal(str(row["cost_price"]))
            reorder_level = int(row["reorder_level"])
        except (ValueError, InvalidOperation):
            failed += 1
            errors.append(f"Row {line_no}: quantity/cost_price/reorder_level must be numeric")
            continue

        if quantity < 0 or cost_price < 0 or reorder_level < 0:
            failed += 1
            errors.append(f"Row {line_no}: numeric fields cannot be negative")
            continue

        warehouse = warehouse_cache.get(warehouse_code)
        if warehouse is None:
            failed += 1
            errors.append(f"Row {line_no}: unknown warehouse code '{warehouse_code}'")
            continue

        category = category_cache.get(category_name)
        if category is None and category_name:
            category = Category(name=category_name)
            db.add(category)
            db.flush()
            category_cache[category_name] = category

        product = db.query(Product).filter(Product.sku == sku).first()
        if product is None:
            product = Product(
                sku=sku,
                name=name,
                category_id=category.id if category else None,
                unit_price=cost_price * Decimal("1.4"),
                cost_price=cost_price,
                reorder_level=reorder_level,
                reorder_quantity=max(reorder_level * 2, 10),
                status=ProductStatus.ACTIVE,
            )
            db.add(product)
            db.flush()
        else:
            product.cost_price = cost_price
            product.reorder_level = reorder_level

        if quantity > 0:
            apply_stock_movement(
                db,
                product_id=product.id,
                warehouse_id=warehouse.id,
                movement_type=MovementType.ADJUSTMENT_IN,
                quantity=quantity,
                created_by_id=imported_by_id,
                reference_number="CSV-IMPORT",
                reason="Bulk CSV import",
                commit=False,
            )

        successful += 1

    db.commit()

    return {
        "total_rows": total_rows,
        "successful": successful,
        "failed": failed,
        "duplicates": duplicates,
        "errors": errors[:50],  # cap so a bad file doesn't blow up the response
    }
