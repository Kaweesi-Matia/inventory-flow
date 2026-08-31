import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.stock_movement import MovementType


class InventoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_on_hand: int
    quantity_reserved: int
    product_name: str | None = None
    product_sku: str | None = None
    reorder_level: int = 0
    warehouse_name: str | None = None

    @property
    def available_quantity(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved


class StockAdjustment(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    # Positive to add stock (ADJUSTMENT_IN), negative to remove (ADJUSTMENT_OUT).
    quantity_delta: int = Field(
        description="Signed quantity: positive adds stock, negative removes it"
    )
    reason: str = Field(min_length=1, max_length=500)


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    movement_type: MovementType
    quantity: int
    reference_number: str | None
    reason: str | None
    created_by_id: uuid.UUID
    created_at: datetime
