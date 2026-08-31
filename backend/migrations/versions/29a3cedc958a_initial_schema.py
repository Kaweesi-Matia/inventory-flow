"""initial schema

Revision ID: 29a3cedc958a
Revises:
Create Date: 2026-08-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "29a3cedc958a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = postgresql.ENUM(
        "ADMIN", "INVENTORY_MANAGER", "WAREHOUSE_MANAGER", "PROCUREMENT_MANAGER", "SALES_USER",
        name="user_role",
    )
    product_status = postgresql.ENUM("ACTIVE", "INACTIVE", "DISCONTINUED", name="product_status")
    supplier_status = postgresql.ENUM("ACTIVE", "INACTIVE", name="supplier_status")
    warehouse_status = postgresql.ENUM("ACTIVE", "INACTIVE", name="warehouse_status")
    movement_type = postgresql.ENUM(
        "PURCHASE_RECEIPT", "SALE", "TRANSFER_IN", "TRANSFER_OUT", "ADJUSTMENT_IN",
        "ADJUSTMENT_OUT", "RETURN", "DAMAGE", "LOSS", name="movement_type",
    )
    po_status = postgresql.ENUM(
        "DRAFT", "SUBMITTED", "APPROVED", "PARTIALLY_RECEIVED", "RECEIVED", "CANCELLED",
        name="purchase_order_status",
    )
    transfer_status = postgresql.ENUM(
        "PENDING", "APPROVED", "IN_TRANSIT", "RECEIVED", "CANCELLED", name="transfer_status"
    )
    order_status = postgresql.ENUM(
        "PENDING", "CONFIRMED", "RESERVED", "PROCESSING", "FULFILLED", "CANCELLED",
        name="customer_order_status",
    )

   

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "warehouses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("address", sa.String(500)),
        sa.Column("city", sa.String(100)),
        sa.Column("country", sa.String(100)),
        sa.Column("manager_name", sa.String(255)),
        sa.Column("status", warehouse_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_warehouses_code", "warehouses", ["code"])

    op.create_table(
        "warehouse_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "warehouse_id", name="uq_warehouse_users_user_warehouse"),
    )

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sku", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(2000)),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("reorder_level", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reorder_quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unit_of_measure", sa.String(32), nullable=False, server_default="unit"),
        sa.Column("status", product_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("unit_price >= 0", name="ck_products_unit_price_non_negative"),
        sa.CheckConstraint("cost_price >= 0", name="ck_products_cost_price_non_negative"),
        sa.CheckConstraint("reorder_level >= 0", name="ck_products_reorder_level_non_negative"),
        sa.CheckConstraint("reorder_quantity >= 0", name="ck_products_reorder_qty_non_negative"),
    )
    op.create_index("ix_products_sku", "products", ["sku"])

    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("contact_person", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("address", sa.String(500)),
        sa.Column("country", sa.String(100)),
        sa.Column("status", supplier_status, nullable=False),
        sa.Column("notes", sa.String(2000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "supplier_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_sku", sa.String(64)),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_id", "product_id", name="uq_supplier_product"),
    )

    op.create_table(
        "inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_on_hand", sa.Integer, nullable=False, server_default="0"),
        sa.Column("quantity_reserved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
        sa.CheckConstraint("quantity_on_hand >= 0", name="ck_inventory_qoh_non_negative"),
        sa.CheckConstraint("quantity_reserved >= 0", name="ck_inventory_reserved_non_negative"),
        sa.CheckConstraint("quantity_reserved <= quantity_on_hand", name="ck_inventory_reserved_lte_on_hand"),
    )
    op.create_index("ix_inventory_product_id", "inventory", ["product_id"])
    op.create_index("ix_inventory_warehouse_id", "inventory", ["warehouse_id"])

    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("movement_type", movement_type, nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("reference_number", sa.String(64)),
        sa.Column("reason", sa.String(500)),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_stock_movements_product_warehouse", "stock_movements", ["product_id", "warehouse_id"])
    op.create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"])
    op.create_index("ix_stock_movements_reference_number", "stock_movements", ["reference_number"])

    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_number", sa.String(32), nullable=False, unique=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("expected_delivery_date", sa.Date),
        sa.Column("status", po_status, nullable=False),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(2000)),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_purchase_orders_order_number", "purchase_orders", ["order_number"])
    op.create_index("ix_purchase_orders_supplier_status", "purchase_orders", ["supplier_id", "status"])

    op.create_table(
        "purchase_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_ordered", sa.Integer, nullable=False),
        sa.Column("quantity_received", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity_ordered > 0", name="ck_po_item_qty_ordered_positive"),
        sa.CheckConstraint("quantity_received >= 0", name="ck_po_item_qty_received_non_negative"),
        sa.CheckConstraint("quantity_received <= quantity_ordered", name="ck_po_item_received_lte_ordered"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_po_item_unit_cost_non_negative"),
    )

    op.create_table(
        "inventory_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transfer_number", sa.String(32), nullable=False, unique=True),
        sa.Column("source_warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destination_warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", transfer_status, nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("notes", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_warehouse_id != destination_warehouse_id", name="ck_transfer_different_warehouses"),
    )
    op.create_index("ix_inventory_transfers_transfer_number", "inventory_transfers", ["transfer_number"])

    op.create_table(
        "inventory_transfer_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transfer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_transfers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_transfer_item_qty_positive"),
    )

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("address", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "customer_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_number", sa.String(32), nullable=False, unique=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("total_amount >= 0", name="ck_customer_order_total_non_negative"),
    )
    op.create_index("ix_customer_orders_order_number", "customer_orders", ["order_number"])
    op.create_index("ix_customer_orders_status", "customer_orders", ["status"])

    op.create_table(
        "customer_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_item_qty_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_order_item_price_non_negative"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("extra_metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("customer_order_items")
    op.drop_table("customer_orders")
    op.drop_table("customers")
    op.drop_table("inventory_transfer_items")
    op.drop_table("inventory_transfers")
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
    op.drop_table("stock_movements")
    op.drop_table("inventory")
    op.drop_table("supplier_products")
    op.drop_table("suppliers")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("warehouse_users")
    op.drop_table("warehouses")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_name in (
        "customer_order_status", "transfer_status", "purchase_order_status", "movement_type",
        "warehouse_status", "supplier_status", "product_status", "user_role",
    ):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
