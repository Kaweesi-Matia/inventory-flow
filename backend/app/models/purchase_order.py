import enum
import uuid

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    order_date: Mapped[Date] = mapped_column(Date, nullable=False)
    expected_delivery_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(PurchaseOrderStatus, name="purchase_order_status"),
        nullable=False,
        default=PurchaseOrderStatus.DRAFT,
    )
    total_cost: Mapped[Numeric] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    warehouse: Mapped["Warehouse"] = relationship()
    created_by: Mapped["User"] = relationship()
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_purchase_orders_supplier_status", "supplier_id", "status"),
    )


class PurchaseOrderItem(Base, TimestampMixin):
    __tablename__ = "purchase_order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_cost: Mapped[Numeric] = mapped_column(Numeric(12, 2), nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()

    __table_args__ = (
        CheckConstraint("quantity_ordered > 0", name="ck_po_item_qty_ordered_positive"),
        CheckConstraint("quantity_received >= 0", name="ck_po_item_qty_received_non_negative"),
        CheckConstraint(
            "quantity_received <= quantity_ordered", name="ck_po_item_received_lte_ordered"
        ),
        CheckConstraint("unit_cost >= 0", name="ck_po_item_unit_cost_non_negative"),
    )

    @property
    def total_cost(self) -> Numeric:
        return self.quantity_ordered * self.unit_cost

    @property
    def quantity_remaining(self) -> int:
        return self.quantity_ordered - self.quantity_received
