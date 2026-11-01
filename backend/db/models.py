from sqlmodel import Relationship, SQLModel, Field
from uuid import uuid4 , UUID
from enum import Enum
from sqlalchemy import Column, Enum as SAEnum , DateTime
from datetime import datetime,timezone
from typing import Optional

class DeliveryStatus(str, Enum):
    ORDER_RECEIVED = "order_received"
    BOOKED = "booked"
    PICKUP_SCHEDULED = "pickup_scheduled"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit" #On the way 
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    DELIVERY_FAILED = "delivery_failed"
    RETURNED = "returned"
    CANCELLED = "cancelled" 
    PICKUP_FAILED = "pickup_failed"


class CarrierType(str, Enum):
    IN_HOUSE = "in_house"
    OUTSOURCED = "outsourced"

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    DELIVERY_AGENT = "delivery_agent"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def ts_field():
    return Field(default_factory=utc_now, sa_type=DateTime(timezone=True))

class User(SQLModel, table = True):
    id:UUID  = Field(default_factory = uuid4 , primary_key =  True)
    name:str
    email:str = Field(unique=True)
    password:str
    role: Role = Field(
            default=Role.USER,
            sa_column=Column(
                SAEnum(
                    Role,
                    native_enum=False,
                    length=20,
                    values_callable=lambda e: [m.value for m in e],
                ),
                nullable=False,
            ),
        )
    orders: list["Order"] = Relationship(back_populates="user")
    created_at: datetime = ts_field()
    


class Order(SQLModel, table = True):
    id:UUID = Field(default_factory = uuid4 , primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    order_name:str
    delivery_status: DeliveryStatus = Field(
    default=DeliveryStatus.ORDER_RECEIVED,
        sa_column=Column(
            SAEnum(
                DeliveryStatus,
                native_enum=False,
                length=30,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
            index=True,
        ),
    )
    user: User = Relationship(back_populates="orders")
    tracks: list["Track"] = Relationship(back_populates="order")
    ship: Optional["Ship"] = Relationship(
        back_populates="order", sa_relationship_kwargs={"uselist": False}
    )
    created_at: datetime = ts_field()


class Track(SQLModel,table = True):
    id:UUID = Field(default_factory = uuid4 , primary_key=True)
    order_id:UUID = Field(foreign_key="order.id")
    order: Order = Relationship(back_populates = "tracks")
    location:str
    created_at: datetime = ts_field()


class DeliveryAgent(SQLModel, table = True):
    id:UUID = Field(default_factory = uuid4 , primary_key=True)
    carrier_type: CarrierType = Field(
        default=CarrierType.OUTSOURCED,
        sa_column=Column(
            SAEnum(
                CarrierType,
                native_enum=False,
                length=20,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        ),
    )
    name:str
    phone:str
    created_at: datetime = ts_field()


class Ship(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="order.id", unique=True)
    order: Order = Relationship(back_populates="ship")
    created_at: datetime = ts_field()
