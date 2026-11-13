from fastapi import APIRouter, HTTPException , Depends

from sqlmodel import Session , select
from backend.services.auth import get_current_client
from db.schema import ShipmentEventIn
from db.models import Client, Order, Shipment
from db.engine import get_session
from services.kafka import publish_event
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/event")
def register_event(
    data: ShipmentEventIn,
    client: Client = Depends(get_current_client),
    session: Session = Depends(get_session)
):
    existing_order = session.exec(
        select(Order).where(
            Order.client_id == client.id,
            Order.external_order_id == data.external_order_id
        )
    ).first()

    if existing_order:
        raise HTTPException(
            status_code=409,
            detail="Order already registered"
        )

    try:
        order = Order(
            client_id=client.id,
            external_order_id=data.external_order_id,
            order_name=data.external_order_id,
            price=data.order_price,
            quantity=data.order_quantity
        )

        session.add(order)
        session.flush()

        shipment = Shipment(
            order_id=order.id,
            pickup_address=data.pickup_address.address,
            delivery_address=data.delivery_address.address
        )

        session.add(shipment)
        session.commit()

        session.refresh(order)
        session.refresh(shipment)

    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to register shipment"
        )

    event = {
        "event_type": "ShipmentCreated",
        "order_id": str(order.id),
        "shipment_id": str(shipment.id),
        "client_id": str(client.id)
    }

    try:
        publish_event(
            "Shipment-created",
            key=str(shipment.id),
            value=event
        )
    except Exception:
        # TODO -> Retry publishing
        logger.exception("Failed to publish ShipmentCreated event")

    return {
        "message": "Shipment registered successfully",
        "order_id": str(order.id),
        "shipment_id": str(shipment.id),
        "status": shipment.status
    }