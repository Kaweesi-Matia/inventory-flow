import enum
import uuid

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class WarehouseStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manager_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[WarehouseStatus] = mapped_column(
        Enum(WarehouseStatus, name="warehouse_status"),
        nullable=False,
        default=WarehouseStatus.ACTIVE,
    )

    user_assignments: Mapped[list["WarehouseUser"]] = relationship(back_populates="warehouse")
    inventory_records: Mapped[list["Inventory"]] = relationship(back_populates="warehouse")
