import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.purchase_order import PurchaseOrderStatus


class PurchaseOrderItemIn(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    warehouse_id: uuid.UUID
    items: list[PurchaseOrderItemIn]
    expected_delivery_date: date | None = None
    notes: str | None = None


class PurchaseOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    quantity_ordered: int
    quantity_received: int
    unit_cost: Decimal


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    supplier_id: uuid.UUID
    warehouse_id: uuid.UUID
    order_date: date
    expected_delivery_date: date | None
    status: PurchaseOrderStatus
    total_cost: Decimal
    items: list[PurchaseOrderItemOut]


class ReceiveLine(BaseModel):
    item_id: uuid.UUID
    quantity_received: int = Field(gt=0)


class PurchaseOrderReceive(BaseModel):
    receipts: list[ReceiveLine]
