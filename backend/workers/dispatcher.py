import logging
from sqlmodel import Session

from db.models import Shipment, DeliveryStatus
from services.events import EventEnvelope, EventType
from db.schema import NearbyAgent
from uuid import UUID
from services.redis_client import redis_client as redis
import os

from workers.base import run_consumer

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,  
)


def on_shipment_created(env: EventEnvelope, session: Session) -> None:
    shipment = session.get(Shipment, env.shipment_id)
    if shipment is None or shipment.status != DeliveryStatus.ORDER_RECEIVED:
        return
    logger.info("dispatching shipment %s", shipment.id)
    # next: move to PICKUP_PENDING, find agent, claim, assignment, outbox
    shipment.status = DeliveryStatus.PICKUP_PENDING

    agents = find_nearby_agents(shipment.pickup_lat , shipment.pickup_lng)





def find_nearby_agents(
    lat: float, lng: float, radius_km: float = 3, exclude: set[UUID] | None = None, limit: int = 10
) -> list[NearbyAgent]:
    raw = redis.geosearch(
        "agents:available",
        longitude=lng, latitude=lat,          # longitude first
        radius=radius_km, unit="km",
        sort="ASC", count=limit + len(exclude or ()),
        withdist=True,
    )
    agents = [NearbyAgent(agent_id=UUID(name), distance_km=dist) for name, dist in raw]
    return [a for a in agents if a.agent_id not in (exclude or set())][:limit]


HANDLERS = {EventType.SHIPMENT_CREATED: on_shipment_created}


def main():
    run_consumer("dispatcher", "shipment-events", HANDLERS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()