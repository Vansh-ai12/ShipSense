from db.models import Shipment , AgentAvailability , AgentStatus
from sqlmodel import Session
from fastapi import Depends
from db.engine import get_session
from services.events import EventEnvelope

def after_shipment_created(ev:EventEnvelope, session:Session = Depends(get_session)):
    
    return