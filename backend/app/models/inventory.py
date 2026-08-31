import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Inventory(Base, TimestampMixin):
    """
    One row per (product, warehouse) pair. This is the single source of
    truth for "how much stock do we have, and where".

    quantity_on_hand: physical units sitting in the warehouse.
    quantity_reserved: units allocated to confirmed-but-unfulfilled orders.
    available = quantity_on_hand - quantity_reserved (never persisted,
    always computed, so it can never drift out of sync).

    Both quantity columns are protected by CHECK constraints at the DB
    level — the application must never rely solely on Python-side checks
    for this invariant, since concurrent transactions could otherwise
    race past an in-memory check.
    """

    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    product: Mapped["Product"] = relationship(back_populates="inventory_records")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="inventory_records")

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
        CheckConstraint("quantity_on_hand >= 0", name="ck_inventory_qoh_non_negative"),
        CheckConstraint("quantity_reserved >= 0", name="ck_inventory_reserved_non_negative"),
        CheckConstraint(
            "quantity_reserved <= quantity_on_hand", name="ck_inventory_reserved_lte_on_hand"
        ),
    )

    @property
    def available_quantity(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved
