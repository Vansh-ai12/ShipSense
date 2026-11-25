import logging
from uuid import UUID

from sqlalchemy import update
from sqlmodel import Session, select

from db.models import (Shipment, DeliveryStatus, AgentAvailability, AgentStatus,
                       ShipmentAssignment, utc_now)
from db.schema import NearbyAgent
from services.events import EventEnvelope, EventType, add_outbox
from services.redis_client import redis_client as redis
from workers.base import run_consumer

logger = logging.getLogger(__name__)


def find_nearby_agents(lat, lng, radius_km=3, exclude=None, limit=10) -> list[NearbyAgent]:
    exclude = exclude or set()
    raw = redis.geosearch("agents:available", longitude=lng, latitude=lat,
                          radius=radius_km, unit="km", sort="ASC",
                          count=limit + len(exclude), withdist=True)
    agents = [NearbyAgent(agent_id=UUID(name), distance_km=dist) for name, dist in raw]
    return [a for a in agents if a.agent_id not in exclude][:limit]


def claim_agent(session: Session, agent_id: UUID, shipment_id: UUID) -> bool:
    res = session.execute(
        update(AgentAvailability)
        .where(AgentAvailability.agent_id == agent_id,
               AgentAvailability.status == AgentStatus.AVAILABLE)
        .values(status=AgentStatus.ASSIGNED,
                current_shipment_id=shipment_id, updated_at=utc_now())
    )
    return res.rowcount == 1


def on_shipment_created(env: EventEnvelope, session: Session) -> None:
    res = session.execute(
        update(Shipment)
        .where(Shipment.id == env.shipment_id,
               Shipment.status == DeliveryStatus.ORDER_RECEIVED)
        .values(status=DeliveryStatus.PICKUP_PENDING, updated_at=utc_now())
    )
    if res.rowcount == 0:
        return                                   # already handled or cancelled

    offer_to_next_agent(session, session.get(Shipment, env.shipment_id))

def offer_to_next_agent(session: Session, shipment: Shipment) -> None:
    tried = set(session.exec(
        select(ShipmentAssignment.agent_id)
        .where(ShipmentAssignment.shipment_id == shipment.id)
    ).all())

    for cand in find_nearby_agents(shipment.pickup_lat, shipment.pickup_lng, exclude=tried):
        if claim_agent(session, cand.agent_id, shipment.id):
            session.add(ShipmentAssignment(shipment_id=shipment.id, agent_id=cand.agent_id))
            add_outbox(session, shipment.id, EventType.AGENT_OFFERED,
                       {"agent_id": str(cand.agent_id)})
            redis.zrem("agents:available", str(cand.agent_id))   # hide from other searches
            return

    add_outbox(session, shipment.id, EventType.NO_AGENT_AVAILABLE)


def on_offer_closed(env: EventEnvelope, session: Session) -> None:
    shipment = session.get(Shipment, env.shipment_id)
    if not shipment or shipment.status != DeliveryStatus.PICKUP_PENDING:
        return                                   # moved on, nothing to re-offer
    offer_to_next_agent(session, shipment)


HANDLERS = {
    EventType.SHIPMENT_CREATED: on_shipment_created,
    EventType.OFFER_DECLINED: on_offer_closed,
    EventType.OFFER_EXPIRED: on_offer_closed,
}

def main():
    run_consumer("dispatcher", "shipment-events", HANDLERS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()