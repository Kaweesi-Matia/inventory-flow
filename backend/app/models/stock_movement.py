import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class MovementType(str, enum.Enum):
    PURCHASE_RECEIPT = "PURCHASE_RECEIPT"
    SALE = "SALE"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"
    RETURN = "RETURN"
    DAMAGE = "DAMAGE"
    LOSS = "LOSS"


class StockMovement(Base, TimestampMixin):
    """
    Append-only ledger. Every single inventory mutation — regardless of
    where it originates (PO receiving, transfers, order fulfillment,
    manual adjustment) — must write exactly one row here in the SAME
    transaction as the inventory update. This is what makes the system
    auditable: quantity_on_hand can always be reconstructed by summing
    signed movement quantities for a product+warehouse.

    Movements are never updated or deleted by application code.
    """

    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, name="movement_type"), nullable=False
    )
    # Signed quantity: positive for inbound movements, negative for outbound.
    # Storing it signed (rather than always-positive + inferring sign from
    # type) makes SUM(quantity) a correct running balance directly in SQL.
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    product: Mapped["Product"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()
    created_by: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_stock_movements_product_warehouse", "product_id", "warehouse_id"),
        Index("ix_stock_movements_created_at", "created_at"),
    )
