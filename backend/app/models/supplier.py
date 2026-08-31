import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class SupplierStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[SupplierStatus] = mapped_column(
        Enum(SupplierStatus, name="supplier_status"), nullable=False, default=SupplierStatus.ACTIVE
    )
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    product_links: Mapped[list["SupplierProduct"]] = relationship(back_populates="supplier")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="supplier")


class SupplierProduct(Base, TimestampMixin):
    """Which suppliers can supply which products, and at what typical cost."""

    __tablename__ = "supplier_products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    supplier_sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_cost: Mapped[Numeric] = mapped_column(Numeric(12, 2), nullable=False)

    supplier: Mapped["Supplier"] = relationship(back_populates="product_links")
    product: Mapped["Product"] = relationship(back_populates="supplier_links")

    __table_args__ = (
        UniqueConstraint("supplier_id", "product_id", name="uq_supplier_product"),
    )
