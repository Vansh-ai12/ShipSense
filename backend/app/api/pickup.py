# app/api/pickup.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlmodel import Session

from db.engine import get_session
from db.models import (AgentAvailability, AgentStatus, AssignmentStatus,
                       DeliveryStatus, Shipment, ShipmentAssignment, utc_now)
from services.events import EventType, add_outbox

router = APIRouter()


def _respond(session: Session, shipment_id: UUID, agent_id: UUID, new_status: AssignmentStatus) -> bool:
    """Move an OFFERED assignment to new_status. Returns False if it was not OFFERED."""
    res = session.execute(
        update(ShipmentAssignment)
        .where(ShipmentAssignment.shipment_id == shipment_id,
               ShipmentAssignment.agent_id == agent_id,
               ShipmentAssignment.status == AssignmentStatus.OFFERED)
        .values(status=new_status, responded_at=utc_now())
    )
    return res.rowcount == 1


@router.post("/shipments/{shipment_id}/accept")
def accept_offer(shipment_id: UUID, agent_id: UUID, session: Session = Depends(get_session)):
    # 1. the offer must still be open (timeout or decline may have closed it)
    if not _respond(session, shipment_id, agent_id, AssignmentStatus.ACCEPTED):
        session.rollback()
        raise HTTPException(409, "Offer is no longer open")

    # 2. guarded shipment transition
    res = session.execute(
        update(Shipment)
        .where(Shipment.id == shipment_id,
               Shipment.status == DeliveryStatus.PICKUP_PENDING)
        .values(status=DeliveryStatus.AGENT_ASSIGNED, updated_at=utc_now())
    )
    if res.rowcount == 0:                       # e.g. shipment was cancelled meanwhile
        session.rollback()
        raise HTTPException(409, "Shipment is not awaiting an agent")

    add_outbox(session, shipment_id, EventType.AGENT_ASSIGNED, {"agent_id": str(agent_id)})
    session.commit()
    return {"status": "agent_assigned"}


@router.post("/shipments/{shipment_id}/decline")
def decline_offer(shipment_id: UUID, agent_id: UUID, session: Session = Depends(get_session)):
    if not _respond(session, shipment_id, agent_id, AssignmentStatus.DECLINED):
        session.rollback()
        raise HTTPException(409, "Offer is no longer open")

    # free the agent
    session.execute(
        update(AgentAvailability)
        .where(AgentAvailability.agent_id == agent_id,
               AgentAvailability.current_shipment_id == shipment_id)
        .values(status=AgentStatus.AVAILABLE, current_shipment_id=None, updated_at=utc_now())
    )

    # tells the dispatcher to find the next agent (it skips agents already tried)
    add_outbox(session, shipment_id, EventType.OFFER_DECLINED,
               {"reason_code": "AGENT_DECLINED", "agent_id": str(agent_id)})
    session.commit()
    return {"status": "declined"}