import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    INVENTORY_MANAGER = "INVENTORY_MANAGER"
    WAREHOUSE_MANAGER = "WAREHOUSE_MANAGER"
    PROCUREMENT_MANAGER = "PROCUREMENT_MANAGER"
    SALES_USER = "SALES_USER"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.SALES_USER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    warehouse_assignments: Mapped[list["WarehouseUser"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email} ({self.role})>"


class WarehouseUser(Base, TimestampMixin):
    """
    Many-to-many assignment of users to warehouses they're authorized to
    operate on (used mainly for WAREHOUSE_MANAGER scoping).
    """

    __tablename__ = "warehouse_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="warehouse_assignments")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="user_assignments", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("user_id", "warehouse_id", name="uq_warehouse_users_user_warehouse"),
    )
