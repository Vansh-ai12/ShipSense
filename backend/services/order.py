from fastapi import Depends, HTTPException, status
from sqlalchemy import update
from sqlmodel import Session
from db.models import Order, User
from db.engine import get_session , engine
from db.schema import OrderCreate , OrderCreatedEvent
from services.auth import get_current_user
from kafka import KafkaProducer , KafkaConsumer
from db.models import AgentAvailability
from uuid import UUID
import json
import redis

from db.models import AgentAvailability, AgentStatus

producer = KafkaProducer(
        bootstrap_servers='localhost:9094',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
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
    "created_at": new_order.created_at.isoformat(),
    "pickup_location": {
        "longitude": order.longitude,
        "latitude": order.latitude
    },

    "product_id":order.product_id   #Listed product ID
    }

    producer.send("orders", value=event)
    
    return {"message": "Order created successfully", "order_id": str(new_order.id)}



def add_agents_locations(locations: list[dict]):
    r = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True
    )

    try:
        for agent in locations:
            agent_id = agent["agent_id"]
            longitude, latitude = agent["location"]

            r.geoadd(
                "nearby-agents",
                (longitude, latitude, agent_id)
            )

        return r.zrange("nearby-agents", 0, -1)

    finally:
        r.close()



def find_nearby_agents(longitude: float, latitude: float, radius: float = 5):
    r = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True
    )

    try:
        nearby = r.geosearch(
            "nearby-agents",
            longitude=longitude,
            latitude=latitude,
            radius=radius,
            unit="km",
            withdist=True,
            withcoord=True,
            sort="ASC"
        )

        result = []

        for agent_id, distance, coordinates in nearby:
            result.append({
                "agent_id": agent_id,
                "distance_km": float(distance),
                "longitude": float(coordinates[0]),
                "latitude": float(coordinates[1])
            })

        return result

    finally:
        r.close()





def reserve_agent(
    order_id: UUID,
    agent_id: UUID,
    session: Session
) -> bool:

    try:
        statement = (
            update(AgentAvailability)
            .where(
                AgentAvailability.agent_id == agent_id,
                AgentAvailability.status == AgentStatus.AVAILABLE,
                AgentAvailability.current_order_id.is_(None)
            )
            .values(
                status=AgentStatus.ASSIGNED,
                current_order_id=order_id
            )
        )

        result = session.exec(statement)

        session.commit()

        return result.rowcount == 1

    except Exception:
        session.rollback()
        raise

def process_order_event(event:OrderCreatedEvent):
    order_id = event.order_id

    longitude = event.pickup_location.longitude
    latitude = event.pickup_location.latitude

   
    candidates = find_nearby_agents(
        longitude,
        latitude,
        radius=5
    )

    if not candidates:
        print(f"No nearby agents for order {order_id}")
        return

    
    for candidate in candidates:
        agent_id = candidate["agent_id"]

        with Session(engine) as session:
            assigned = reserve_agent(
                agent_id=agent_id,
                order_id=order_id,
                session=session
            )
        

        if assigned:

            assignment_event = {
                "event_type": "AgentAssigned",
                "order_id": order_id,
                "agent_id": agent_id
            }

            producer.send(
                "agent-assigned",
                value=assignment_event
            ).get(timeout=10)

            print("Assignment successful:", assignment_event)
            return

    print(f"No available agents for order {order_id}")
    


def run_order_event():
    consumer = KafkaConsumer(
        'orders',
        bootstrap_servers='localhost:9094',
        group_id='order-service-group',
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )

    for message in consumer:
        try:
            event = OrderCreatedEvent.model_validate(message.value)
            process_order_event(event)

        except Exception as e:
            print(f"Failed to process event: {e}")