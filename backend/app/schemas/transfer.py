import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.transfer import TransferStatus


class TransferItemIn(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)


class TransferCreate(BaseModel):
    source_warehouse_id: uuid.UUID
    destination_warehouse_id: uuid.UUID
    items: list[TransferItemIn]
    notes: str | None = None


class TransferItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transfer_number: str
    source_warehouse_id: uuid.UUID
    destination_warehouse_id: uuid.UUID
    status: TransferStatus
    items: list[TransferItemOut]
