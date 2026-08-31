import enum
import uuid

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class CustomerOrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    RESERVED = "RESERVED"
    PROCESSING = "PROCESSING"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    orders: Mapped[list["CustomerOrder"]] = relationship(back_populates="customer")


class CustomerOrder(Base, TimestampMixin):
    __tablename__ = "customer_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    order_date: Mapped[Date] = mapped_column(Date, nullable=False)
    status: Mapped[CustomerOrderStatus] = mapped_column(
        Enum(CustomerOrderStatus, name="customer_order_status"),
        nullable=False,
        default=CustomerOrderStatus.PENDING,
    )
    total_amount: Mapped[Numeric] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    warehouse: Mapped["Warehouse"] = relationship()
    created_by: Mapped["User"] = relationship()
    items: Mapped[list["CustomerOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_customer_order_total_non_negative"),
    )


class CustomerOrderItem(Base, TimestampMixin):
    __tablename__ = "customer_order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Numeric] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["CustomerOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_item_qty_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_item_price_non_negative"),
    )

    @property
    def total(self) -> Numeric:
        return self.quantity * self.unit_price
