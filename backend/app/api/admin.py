import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.database.connection import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole, WarehouseUser
from app.models.warehouse import Warehouse
from app.schemas.auth import UserOut, WarehouseAssignmentIn, to_user_out

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return [to_user_out(u) for u in db.query(User).order_by(User.full_name).all()]


@router.put("/users/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: uuid.UUID,
    role: UserRole,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    if user_id == _admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own role")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = role
    db.add(
        AuditLog(
            user_id=_admin.id,
            action="USER_ROLE_CHANGE",
            resource_type="user",
            resource_id=str(user_id),
            extra_metadata={"new_role": role.value},
        )
    )
    db.commit()
    db.refresh(user)
    return to_user_out(user)


@router.put("/users/{user_id}/warehouses", response_model=UserOut)
def set_user_warehouses(
    user_id: uuid.UUID,
    payload: WarehouseAssignmentIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    warehouse_ids = list(dict.fromkeys(payload.warehouse_ids))
    if warehouse_ids:
        found = {row[0] for row in db.query(Warehouse.id).filter(Warehouse.id.in_(warehouse_ids)).all()}
        missing = [wid for wid in warehouse_ids if wid not in found]
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more warehouses do not exist")

    db.query(WarehouseUser).filter(WarehouseUser.user_id == user_id).delete(synchronize_session="fetch")
    for warehouse_id in warehouse_ids:
        db.add(WarehouseUser(user_id=user_id, warehouse_id=warehouse_id))
    db.add(
        AuditLog(
            user_id=_admin.id,
            action="USER_WAREHOUSE_ASSIGNMENT",
            resource_type="user",
            resource_id=str(user_id),
            extra_metadata={"warehouse_ids": [str(wid) for wid in warehouse_ids]},
        )
    )
    db.commit()
    db.refresh(user)
    return to_user_out(user)


@router.get("/audit-logs")
def list_audit_logs(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN)),
    limit: int = 200,
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": str(l.id),
            "user_id": str(l.user_id) if l.user_id else None,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "created_at": l.created_at.isoformat(),
            "metadata": l.extra_metadata,
        }
        for l in logs
    ]
