from fastapi import Depends, HTTPException, status
from sqlmodel import Session , select

from sqlalchemy import update
from db.models import Product , Order ,AgentAvailability , DeliveryStatus , AgentStatus, Track
from uuid import UUID
from db.schema import PickUpDetails , PickupResponse
from kafka import KafkaProducer
import json
from services.states import ALLOWED
import os

_producer = None

def publish_event(topic: str, key: str, value: dict):
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=os.environ.get("localhost:9094"),
            key_serializer=lambda k: k.encode(),
            value_serializer=lambda v: json.dumps(v).encode(),
        )
    _producer.send(topic, key=key, value=value).get(timeout=5)



def check_warehouse_availability(
    order_id: UUID,
    product_id: UUID,
    session: Session
) -> bool:

    product = session.get(Product, product_id)
    order = session.get(Order, order_id)

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if product.stock_quantity <= 0:
        raise HTTPException(
            status_code=409,
            detail="Product is out of stock"
        )

    return True


def confirm_pickup(session: Session, order_id: UUID, agent_id: UUID):
    assigned = session.exec(select(AgentAvailability).where(
        AgentAvailability.agent_id == agent_id,
        AgentAvailability.current_order_id == order_id,
    )).first()
    if not assigned:
        raise HTTPException(404, "Order not found")

    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if order.delivery_status == DeliveryStatus.PICKED_UP:
        return order                                        # a repeat call changes nothing
    if DeliveryStatus.PICKED_UP not in ALLOWED[order.delivery_status]:
        raise HTTPException(409, "Order cannot be picked up in its current state")
    # TODO: verify pickup_code here, when you add codes

    changed = session.execute(
        update(Order)
        .where(Order.id == order_id, Order.delivery_status == DeliveryStatus.AGENT_ASSIGNED)
        .values(delivery_status=DeliveryStatus.PICKED_UP)
    ).rowcount
    if changed != 1:
        session.rollback()
        raise HTTPException(409, "Order was already updated")

    assigned.status = AgentStatus.ON_DELIVERY
    session.add(Track(order_id=order_id, status=DeliveryStatus.PICKED_UP,
                      location="warehouse", agent_id=agent_id))
    session.commit()
    publish_event("shipment-events", key=str(order_id), value={
        "event_type": "ParcelPickedUp", "order_id": str(order_id), "agent_id": str(agent_id)})
    session.refresh(order)
    return order


def report_pickup_failed(session: Session, order_id: UUID, agent_id: UUID, reason: str):
    assigned = session.exec(select(AgentAvailability).where(
        AgentAvailability.agent_id == agent_id,
        AgentAvailability.current_order_id == order_id,
    )).first()
    if not assigned:
        raise HTTPException(404, "Order not found")

    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if DeliveryStatus.PICKUP_FAILED not in ALLOWED[order.delivery_status]:
        raise HTTPException(409, "Pickup cannot be failed in the current state")

    changed = session.execute(
        update(Order)
        .where(Order.id == order_id, Order.delivery_status == DeliveryStatus.AGENT_ASSIGNED)
        .values(delivery_status=DeliveryStatus.PICKUP_FAILED)
    ).rowcount
    if changed != 1:
        session.rollback()
        raise HTTPException(409, "Order was already updated")

    assigned.status = AgentStatus.AVAILABLE                
    assigned.current_order_id = None
    session.add(Track(order_id=order_id, location=f"pickup failed: {reason}"))
    session.commit()
    publish_event("shipment-events", key=str(order_id), value={
        "event_type": "PickupFailed", "order_id": str(order_id),
        "agent_id": str(agent_id), "reason": reason})
    session.refresh(order)
    return order