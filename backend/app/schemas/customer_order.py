import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.customer_order import CustomerOrderStatus


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str | None = None
    phone: str | None = None
    address: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    address: str | None


class CustomerOrderItemIn(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class CustomerOrderCreate(BaseModel):
    customer_id: uuid.UUID
    warehouse_id: uuid.UUID
    items: list[CustomerOrderItemIn]


class CustomerOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: Decimal


class CustomerOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    customer_id: uuid.UUID
    warehouse_id: uuid.UUID
    order_date: date
    status: CustomerOrderStatus
    total_amount: Decimal
    items: list[CustomerOrderItemOut]
