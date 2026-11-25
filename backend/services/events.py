from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlmodel import Session

from db.models import OutboxEvent

SHIPMENT_TOPIC = "shipment-events"


class EventType(str, Enum):
    SHIPMENT_CREATED = "ShipmentCreated"
    AGENT_OFFERED = "AgentOffered"            # new: dispatcher made an offer
    AGENT_ASSIGNED = "AgentAssigned"          # agent accepted
    NO_AGENT_AVAILABLE = "NoAgentAvailable"   # new: nobody to offer to
    PICKUP_FAILED = "PickupFailed"            # declined, timed out, breakdown...
    PARCEL_PICKED_UP = "ParcelPickedUp"       # new
    DELIVERY_FAILED = "DeliveryFailed"
    SHIPMENT_ON_HOLD = "ShipmentOnHold"
    DELIVERED = "Delivered"
    OFFER_DECLINED = "OfferDeclined"
    OFFER_EXPIRED = "OfferExpired"


class EventEnvelope(BaseModel):
    event_id: UUID
    event_type: EventType
    shipment_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    data: dict[str, Any] = Field(default_factory=dict)


def add_outbox(
    session: Session,
    shipment_id: UUID,
    event_type: EventType,
    data: dict[str, Any] | None = None,
) -> UUID:
    """Stage an event in the outbox. It is saved with the caller's transaction, so
    the caller commits (routes) or base.py commits (handlers)."""
    event_id = uuid4()
    env = EventEnvelope(
        event_id=event_id,
        event_type=event_type,
        shipment_id=shipment_id,
        data=data or {},
    )
    session.add(OutboxEvent(
        id=event_id,                      # same id as event_id, never changes on resend
        topic=SHIPMENT_TOPIC,
        key=str(shipment_id),             # keeps one shipment's events ordered
        payload=env.model_dump(mode="json"),
    ))
    return event_id