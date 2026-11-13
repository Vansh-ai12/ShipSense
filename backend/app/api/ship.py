from fastapi import APIRouter, HTTPException , Depends

from sqlmodel import Session , select
from backend.services.auth import get_current_client
from db.schema import ShipmentEventIn
from db.models import Client, Order, Shipment
from db.engine import get_session
router = APIRouter()



@router.post("/event")
def register_event(
    data: ShipmentEventIn,
    client: Client = Depends(get_current_client),
    session: Session = Depends(get_session)
):
    # 1. Check whether this marketplace already submitted this order
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
        # 2. Create Order
        order = Order(
            client_id=client.id,
            external_order_id=data.external_order_id,
            order_name=data.external_order_id,
            price=data.order_price,
            quantity=data.order_quantity
        )

        session.add(order)
        session.flush()  # Generates order.id without committing

        # 3. Create Shipment
        shipment = Shipment(
            order_id=order.id,
            pickup_address=data.pickup_address.address,
            delivery_address=data.delivery_address.address
        )

        session.add(shipment)
        session.commit()

        session.refresh(order)
        session.refresh(shipment)

        return {
            "message": "Shipment registered successfully",
            "order_id": str(order.id),
            "shipment_id": str(shipment.id),
            "status": shipment.status
        }

    except Exception:
        session.rollback()
        raise