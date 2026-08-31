import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.SALES_USER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class WarehouseAssignmentIn(BaseModel):
    warehouse_ids: list[uuid.UUID] = Field(default_factory=list)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    warehouse_ids: list[uuid.UUID] = Field(default_factory=list)
    warehouse_labels: list[str] = Field(default_factory=list)


def to_user_out(user) -> UserOut:
    assignments = list(getattr(user, "warehouse_assignments", None) or [])
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        warehouse_ids=[a.warehouse_id for a in assignments],
        warehouse_labels=[a.warehouse.code for a in assignments if getattr(a, "warehouse", None)],
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
