import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.product import ProductStatus


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_id: uuid.UUID | None = None
    unit_price: Decimal = Field(ge=0)
    cost_price: Decimal = Field(ge=0)
    reorder_level: int = Field(ge=0, default=0)
    reorder_quantity: int = Field(ge=0, default=0)
    unit_of_measure: str = "unit"


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category_id: uuid.UUID | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    cost_price: Decimal | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    reorder_quantity: int | None = Field(default=None, ge=0)
    unit_of_measure: str | None = None
    status: ProductStatus | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str
    description: str | None
    category_id: uuid.UUID | None
    unit_price: Decimal
    cost_price: Decimal
    reorder_level: int
    reorder_quantity: int
    unit_of_measure: str
    status: ProductStatus


class PaginatedProducts(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    parent_id: uuid.UUID | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
