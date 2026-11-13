from sqlmodel import Relationship, SQLModel, Field
from uuid import uuid4 , UUID
from enum import Enum
from sqlalchemy import Column, Enum as SAEnum , DateTime
from datetime import datetime,timezone
from typing import Optional
from db.schema import Location
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
    PICKUP_PENDING = "pickup_pending"
    AGENT_ASSIGNED = "agent_assigned"


class CarrierType(str, Enum):
    IN_HOUSE = "in_house"
    OUTSOURCED = "outsourced"

class Role(str, Enum):
    ADMIN = "admin"



class AgentStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    ON_DELIVERY = "ON_DELIVERY"
    OFFLINE = "OFFLINE"
    BUSY = "BUSY"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def ts_field():
    return Field(default_factory=utc_now, sa_type=DateTime(timezone=True))



class Client(SQLModel, table=True):
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True
    )

    client_name: str = Field(
        unique=True,
        index=True
    )

    api_key_hash: str = Field(unique=True, index=True)

    api_key_prefix: str

    is_active: bool = Field(default=True)


    orders: list["Order"] = Relationship(
        back_populates="client"
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True)
    )


class User(SQLModel, table = True):
    id:UUID  = Field(default_factory = uuid4 , primary_key =  True)
    name:str
    email:str = Field(unique=True)
    password:str
    role: Role = Field(
            default=Role.ADMIN,
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

    created_at: datetime = ts_field()
    


class Order(SQLModel, table = True):
    id:UUID = Field(default_factory = uuid4 , primary_key=True)
    order_name:str
    price: float
    quantity: int
    client_id: UUID = Field(
    foreign_key="client.id",
    index=True
)
    has_cancelled:bool = Field(default=False)
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
    client: "Client" = Relationship(
            back_populates="orders"
        )
    shipment: Optional["Shipment"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"uselist": False}
    )
    created_at: datetime = ts_field()


class Track(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    shipment_id: UUID = Field(
        foreign_key="shipment.id",
        index=True
    )

    shipment: "Shipment" = Relationship(
        back_populates="tracks"
    )
    status: DeliveryStatus = Field(
        sa_column=Column(
            SAEnum(DeliveryStatus, native_enum=False, length=30,
                   values_callable=lambda e: [m.value for m in e]),
            nullable=False,
        )
    )
    location: Optional[str] = None
    note: Optional[str] = None
    agent_id: Optional[UUID] = Field(default=None, foreign_key="deliveryagent.id")
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
    availability: Optional["AgentAvailability"] = Relationship(
        back_populates="agent",
    )
    created_at: datetime = ts_field()


class Shipment(SQLModel, table=True):

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True
    )

    order_id: UUID = Field(
        foreign_key="order.id",
        unique=True,
        index=True
    )

    
    pickup_address: str
    delivery_address: str

    status: DeliveryStatus = Field(
        default=DeliveryStatus.ORDER_RECEIVED,
        sa_column=Column(
            SAEnum(
                DeliveryStatus,
                native_enum=False,
                length=30,
                values_callable=lambda e: [m.value for m in e]
            ),
            nullable=False,
            index=True
        )
    )

    estimated_delivery: Optional[datetime] = None

    order: "Order" = Relationship(
        back_populates="shipment"
    )

    tracks: list["Track"] = Relationship(
        back_populates="shipment"
    )

    created_at: datetime = ts_field()
    updated_at: datetime = ts_field()


class AgentAvailability(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    agent_id: UUID = Field(
        foreign_key="deliveryagent.id",
        unique=True
    )

    status: AgentStatus = Field(
        default=AgentStatus.OFFLINE
    )

    current_shipment_id: UUID | None = Field(
        default=None,
        foreign_key="shipment.id"
    )

    agent: DeliveryAgent = Relationship(
        back_populates="availability"
    )

    last_seen_at: datetime = Field(sa_type=DateTime(timezone=True))
    updated_at: datetime = ts_field()


