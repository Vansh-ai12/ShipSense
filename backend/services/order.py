

from fastapi import Depends, HTTPException, status
from sqlmodel import Session
from db.models import Order, User
from db.engine import get_session
from backend.db.schema import OrderCreate
from backend.services.auth import get_current_user
from kafka import KafkaProducer , KafkaConsumer
import json

producer = KafkaProducer(
    bootstrap_servers='localhost:9094',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'orders',
    bootstrap_servers='localhost:9094',
    group_id='order-service-group',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)

def create_order(order:OrderCreate , session: Session = Depends(get_session) , user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if order.user_id != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to create an order for this user")
    userOld = session.get(User, order.user_id)
    if not userOld:  
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    new_order = Order(
        user_id=order.user_id,
        order_name=order.order_name,
        price=order.price,
        quantity=order.quantity,
        user=userOld,
    )
    try:
        session.add(new_order)
        session.commit()
        session.refresh(new_order)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create order")

    event = {
    "event_type": "OrderCreated",
    "order_id": str(new_order.id),
    "user_id": str(new_order.user_id),
    "order_name": new_order.order_name,
    "price": new_order.price,
    "quantity": new_order.quantity,
    "created_at": new_order.created_at.isoformat()
    }

    producer.send("orders", value=event)
    
    return {"message": "Order created successfully", "order_id": str(new_order.id)}


def assignDeliveryAgent():
    return