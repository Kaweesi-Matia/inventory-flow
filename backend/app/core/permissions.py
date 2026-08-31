"""
Role-based authorization.

Every protected route declares which roles may call it via
`require_roles(...)`. This is enforced server-side on every request —
the frontend hiding a menu item is a UX nicety, never the actual gate.
"""
from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import false

from app.models.user import User, UserRole, WarehouseUser
from app.services.auth_service import get_current_user

# These roles see every warehouse. WAREHOUSE_MANAGER and SALES_USER are
# limited to rows in warehouse_users (an empty assignment means no access).
CROSS_WAREHOUSE_ROLES = {
    UserRole.ADMIN,
    UserRole.INVENTORY_MANAGER,
    UserRole.PROCUREMENT_MANAGER,
}

SCOPED_ROLES = {
    UserRole.WAREHOUSE_MANAGER,
    UserRole.SALES_USER,
}


def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Returns a FastAPI dependency that raises 403 unless the current
    user's role is in `allowed_roles`. ADMIN is never implied — pass
    UserRole.ADMIN explicitly wherever admins should have access.
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' is not permitted to perform this action",
            )
        return current_user

    return dependency


def assigned_warehouse_ids(user: User, db: Session) -> list[UUID] | None:
    """
    None = unrestricted (admin / inventory manager / procurement).
    A list (possibly empty) = warehouse-scoped roles.
    """
    if user.role in CROSS_WAREHOUSE_ROLES:
        return None
    rows = db.query(WarehouseUser.warehouse_id).filter(WarehouseUser.user_id == user.id).all()
    return [row[0] for row in rows]


def apply_warehouse_scope(query, column, warehouse_ids: list[UUID] | None):
    if warehouse_ids is None:
        return query
    if not warehouse_ids:
        return query.filter(false())
    return query.filter(column.in_(warehouse_ids))


def assert_warehouse_access(user: User, warehouse_id: UUID, db: Session) -> None:
    """
    Raises 403 unless `user` is authorized to operate on `warehouse_id`.

    ADMIN, INVENTORY_MANAGER, and PROCUREMENT_MANAGER see every warehouse.
    WAREHOUSE_MANAGER and SALES_USER are limited to warehouse_users.
    """
    if user.role in CROSS_WAREHOUSE_ROLES:
        return

    assigned = (
        db.query(WarehouseUser)
        .filter(WarehouseUser.user_id == user.id, WarehouseUser.warehouse_id == warehouse_id)
        .first()
    )
    if not assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this warehouse",
        )
