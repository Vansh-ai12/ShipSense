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
    PICKUP_PENDING = "pickup_pending"
    AGENT_ASSIGNED = "agent_assigned"

class PaymentMethod(str, Enum):
    PREPAID = "prepaid"
    COD = "cod"          # cash on delivery

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class CarrierType(str, Enum):
    IN_HOUSE = "in_house"
    OUTSOURCED = "outsourced"

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    DELIVERY_AGENT = "delivery_agent"


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
    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user"
    )
    created_at: datetime = ts_field()
    


class Order(SQLModel, table = True):
    id:UUID = Field(default_factory = uuid4 , primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    order_name:str
    price: float
    quantity: int
    
    product_id: UUID = Field(foreign_key="product.id")
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
    payment_method: PaymentMethod = Field(
        default=PaymentMethod.PREPAID,
        sa_column=Column(
            SAEnum(
                PaymentMethod,
                native_enum=False,
                length=20,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
            server_default="prepaid",
        ),
    )
    payment_status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        sa_column=Column(
            SAEnum(
                PaymentStatus,
                native_enum=False,
                length=20,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
            server_default="pending",
            index=True,
        ),
    )
    pickup_code:str
    code_attempts:int = 3
    user: User = Relationship(back_populates="orders")
    tracks: list["Track"] = Relationship(back_populates="order")
    ship: Optional["Ship"] = Relationship(
        back_populates="order", sa_relationship_kwargs={"uselist": False}
    )
    created_at: datetime = ts_field()


class Track(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="order.id", index=True)
    order: Order = Relationship(back_populates="tracks")
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


class Ship(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="order.id", unique=True)
    order: Order = Relationship(back_populates="ship")
    created_at: datetime = ts_field()


class RefreshToken(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: UUID = Field(foreign_key="user.id")

    token_hash: str

    expires_at: datetime = Field(sa_type=DateTime(timezone=True))

    revoked: bool = False

    created_at: datetime = ts_field()

    user: "User" = Relationship(
        back_populates="refresh_tokens"
    )


class AgentAvailability(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    agent_id: UUID = Field(
        foreign_key="deliveryagent.id",
        unique=True
    )

    status: AgentStatus = Field(
        default=AgentStatus.OFFLINE
    )

    current_order_id: UUID | None = Field(
        default=None,
        foreign_key="order.id"
    )

    agent: DeliveryAgent = Relationship(
        back_populates="availability"
    )

    last_seen_at: datetime = Field(sa_type=DateTime(timezone=True))
    updated_at: datetime = ts_field()


class Product(SQLModel, table = True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title:str
    price:float
    stock_quantity:int
    description: Optional[str] = None
    created_at: datetime = ts_field()