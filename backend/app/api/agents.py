from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db.engine import get_session
from db.models import AgentAvailability, AgentStatus, DeliveryAgent, utc_now
from services.redis_client import redis_client as redis

router = APIRouter()



@router.post("/agents/{agent_id}/ping")
def ping(agent_id: UUID, lat: float, lng: float, session: Session = Depends(get_session)):
    if not session.get(DeliveryAgent, agent_id):
        raise HTTPException(404, "Agent not found")

    avail = session.exec(
        select(AgentAvailability).where(AgentAvailability.agent_id == agent_id)
    ).first()
    if not avail:
        avail = AgentAvailability(agent_id=agent_id, status=AgentStatus.AVAILABLE)
        session.add(avail)
    elif avail.status == AgentStatus.OFFLINE:
        avail.status = AgentStatus.AVAILABLE

    avail.last_seen_at = utc_now()
    avail.updated_at = utc_now()
    session.commit()

    # only free agents are searchable; a busy agent's ping must not put them back
    if avail.status == AgentStatus.AVAILABLE:
        redis.geoadd("agents:available", (lng, lat, str(agent_id)))
    return {"status": avail.status}