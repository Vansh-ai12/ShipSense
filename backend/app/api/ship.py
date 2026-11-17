import logging
from uuid import uuid4  , UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status , Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from db.engine import get_session
from db.models import Client, Order, OutboxEvent, Shipment
from db.schema import ShipmentEventIn
from services.auth import get_current_client , require_roles
from db.schema import ShipmentOut , ClientOut, OrderOut
from db.models import User , Role , DeliveryStatus

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


@router.get("/shipments/{shipment_id}", response_model=ShipmentOut)
def get_shipment(
    shipment_id: UUID,
    user: User = Depends(require_roles(Role.ADMIN)),
    session: Session = Depends(get_session),
):
    shipment = session.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment

@router.get("/client/{client_id}" , response_model=Client)
def get_client(
    client_id: UUID,
    user: User = Depends(require_roles(Role.ADMIN)),
    session: Session = Depends(get_session),
):
    client = session.get(Client,client_id)
    if not client:
        raise HTTPException(status_code=404 , detail = "Client not found")
    
    return client


@router.get("/order/{order_id}" , response_model=OrderOut)
def get_order(
    order_id: UUID,
    user: User = Depends(require_roles(Role.ADMIN)),
    session: Session = Depends(get_session),
):
    order = session.get(Client,order_id)
    if not order:
        raise HTTPException(status_code=404 , detail = "Order not found")
    
    return order


# all clients
@router.get("/clients", response_model=list[ClientOut])
def list_clients(
    limit: int = Query(20, le=100),
    offset: int = 0,
    admin: User = Depends(require_roles(Role.ADMIN)),
    session: Session = Depends(get_session),
):
    return session.exec(select(Client).offset(offset).limit(limit)).all()


# all orders, optionally filtered (covers "orders of a client")
@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    client_id: UUID | None = None,
    status: DeliveryStatus | None = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
    admin: User = Depends(require_roles(Role.ADMIN)),
    session: Session = Depends(get_session),
):
    q = select(Order)
    if client_id:
        q = q.where(Order.client_id == client_id)
    if status:
        q = q.where(Order.delivery_status == status)
    return session.exec(q.order_by(Order.created_at.desc()).offset(offset).limit(limit)).all()


# all shipments of a client: join through Order
@router.get("/shipments", response_model=list[ShipmentOut])
def list_shipments(
    client_id: UUID | None = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
    admin: User = Depends(require_roles(Role.ADMIN)),
    session: Session = Depends(get_session),
):
    q = select(Shipment)
    if client_id:
        q = q.join(Order, Order.id == Shipment.order_id).where(Order.client_id == client_id)
    return session.exec(q.order_by(Shipment.created_at.desc()).offset(offset).limit(limit)).all()