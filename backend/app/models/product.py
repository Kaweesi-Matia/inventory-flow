import enum
import uuid

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class ProductStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISCONTINUED = "DISCONTINUED"


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    unit_price: Mapped[Numeric] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[Numeric] = mapped_column(Numeric(12, 2), nullable=False)
    reorder_level: Mapped[int] = mapped_column(nullable=False, default=0)
    reorder_quantity: Mapped[int] = mapped_column(nullable=False, default=0)
    unit_of_measure: Mapped[str] = mapped_column(String(32), nullable=False, default="unit")
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"), nullable=False, default=ProductStatus.ACTIVE
    )

    category: Mapped["Category | None"] = relationship(back_populates="products")
    inventory_records: Mapped[list["Inventory"]] = relationship(back_populates="product")
    supplier_links: Mapped[list["SupplierProduct"]] = relationship(back_populates="product")

    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="ck_products_unit_price_non_negative"),
        CheckConstraint("cost_price >= 0", name="ck_products_cost_price_non_negative"),
        CheckConstraint("reorder_level >= 0", name="ck_products_reorder_level_non_negative"),
        CheckConstraint("reorder_quantity >= 0", name="ck_products_reorder_qty_non_negative"),
    )
