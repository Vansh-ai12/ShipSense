
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

class EventType(str, Enum):
    SHIPMENT_CREATED = "ShipmentCreated"
    AGENT_ASSIGNED = "AgentAssigned"
    PICKUP_FAILED = "PickupFailed"
    DELIVERY_FAILED = "DeliveryFailed"
    SHIPMENT_ON_HOLD = "ShipmentOnHold"
    DELIVERED = "Delivered"

class EventEnvelope(BaseModel):
    event_id: UUID
    event_type: EventType
    shipment_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    data: dict[str, Any] = {}