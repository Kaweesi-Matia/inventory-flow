import enum
import uuid

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class TransferStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class InventoryTransfer(Base, TimestampMixin):
    __tablename__ = "inventory_transfers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transfer_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    source_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    destination_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, name="transfer_status"), nullable=False, default=TransferStatus.PENDING
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    source_warehouse: Mapped["Warehouse"] = relationship(foreign_keys=[source_warehouse_id])
    destination_warehouse: Mapped["Warehouse"] = relationship(foreign_keys=[destination_warehouse_id])
    created_by: Mapped["User"] = relationship()
    items: Mapped[list["InventoryTransferItem"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "source_warehouse_id != destination_warehouse_id",
            name="ck_transfer_different_warehouses",
        ),
    )


class InventoryTransferItem(Base, TimestampMixin):
    __tablename__ = "inventory_transfer_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transfer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_transfers.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    transfer: Mapped["InventoryTransfer"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()

    __table_args__ = (CheckConstraint("quantity > 0", name="ck_transfer_item_qty_positive"),)
