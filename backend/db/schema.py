from pydantic import BaseModel, ConfigDict , Field

from uuid import UUID

from datetime import datetime

from typing import Optional ,Annotated , Literal

from db.models import DeliveryStatus

class Location(BaseModel):
    address: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "user" 


class UserLogin(BaseModel):
    email: str
    password: str
    role: Optional[str] = "user"  


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str

    class Config:
        orm_mode = True






class ShipmentEventIn(BaseModel):
    external_order_id: str
    pickup_address: Location
    delivery_address: Location
    order_price: float
    order_quantity: int
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None


class ShipmentEventOut(BaseModel):
    order_id:UUID
    shipment_id:UUID
    pickup_address:Location
    delivery_address:Location
    estimated_delivery: datetime


class ShipmentOut(BaseModel):
    id:UUID
    order_id:UUID
    pickup_address:str
    delivery_address:str
    status:DeliveryStatus
    created_at:datetime


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_name: str
    api_key_prefix: str        
    is_active: bool
    created_at: datetime
   


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    order_name: str
    price: float
    quantity: int
    has_cancelled: bool
    created_at: datetime

class OrderCreatedEvent(BaseModel):
    event_type: Literal["OrderCreated"]

    order_id: UUID

    product_id: UUID
    created_at: datetime

    pickup_location: Location


class AgentAssignedEvent(BaseModel):
    event_type: Literal["AgentAssigned"]
    order_id: UUID
    agent_id: str


class PickUpDetails(BaseModel):
    agent_id:UUID
    is_pick:bool
    order_id:UUID


class PickupResponse(BaseModel):
    success: bool
    message: str
    order_id: UUID
    status: str
    reassignment_initiated: bool = False


class NearbyAgent(BaseModel):
    agent_id: UUID
    distance_km: float