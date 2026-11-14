import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from db.engine import get_session
from db.models import Client, Order, OutboxEvent, Shipment
from db.schema import ShipmentEventIn
from services.auth import get_current_client

logger = logging.getLogger(__name__)
router = APIRouter()

SHIPMENT_TOPIC = "shipment-events"


def _find_existing(session: Session, client_id, external_order_id):
    order = session.exec(
        select(Order).where(
            Order.client_id == client_id,
            Order.external_order_id == external_order_id,
        )
    ).first()
    if not order:
        return None, None
    shipment = session.exec(select(Shipment).where(Shipment.order_id == order.id)).first()
    return order, shipment


def _body(order: Order, shipment: Shipment, message: str) -> dict:
    return {
        "message": message,
        "order_id": str(order.id),
        "shipment_id": str(shipment.id),
        "status": shipment.status,
    }


@router.post("/event")
def register_event(
    data: ShipmentEventIn,
    response: Response,
    client: Client = Depends(get_current_client),
    session: Session = Depends(get_session),
):
    # a repeated request returns the same shipment, so a client retry is safe
    order, shipment = _find_existing(session, client.id, data.external_order_id)
    if order and shipment:
        return _body(order, shipment, "Shipment already registered")

    try:
        order = Order(
            client_id=client.id,
            external_order_id=data.external_order_id,
            order_name=data.external_order_id,
            price=data.order_price,
            quantity=data.order_quantity,
        )
        session.add(order)
        session.flush()

        shipment = Shipment(
            order_id=order.id,
            pickup_address=data.pickup_address.address,
            delivery_address=data.delivery_address.address,
        )
        session.add(shipment)
        session.flush()

        event_id = uuid4()
        session.add(OutboxEvent(
            id=event_id,
            topic=SHIPMENT_TOPIC,
            key=str(shipment.id),
            payload={
                "event_id": str(event_id),
                "event_type": "ShipmentCreated",
                "order_id": str(order.id),
                "shipment_id": str(shipment.id),
                "client_id": str(client.id),
            },
        ))
        session.commit()          # order, shipment, and outbox row, all or nothing

    except IntegrityError:        # two requests raced, and the other one won
        session.rollback()
        order, shipment = _find_existing(session, client.id, data.external_order_id)
        if order and shipment:
            return _body(order, shipment, "Shipment already registered")
        logger.exception("Integrity error while registering shipment")
        raise HTTPException(status_code=409, detail="Conflict while registering shipment")

    except Exception:
        session.rollback()
        logger.exception("Failed to register shipment")
        raise HTTPException(status_code=500, detail="Failed to register shipment")

    session.refresh(order)
    session.refresh(shipment)
    response.status_code = status.HTTP_201_CREATED
    return _body(order, shipment, "Shipment registered successfully")