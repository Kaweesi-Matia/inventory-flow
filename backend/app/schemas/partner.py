import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.supplier import SupplierStatus
from app.models.warehouse import WarehouseStatus


class SupplierCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    country: str | None = None
    notes: str | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    contact_person: str | None
    email: str | None
    phone: str | None
    address: str | None
    country: str | None
    status: SupplierStatus
    notes: str | None


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=20)
    address: str | None = None
    city: str | None = None
    country: str | None = None
    manager_name: str | None = None


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    address: str | None
    city: str | None
    country: str | None
    manager_name: str | None
    status: WarehouseStatus
