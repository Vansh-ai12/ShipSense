from pydantic import BaseModel

from uuid import UUID

from datetime import datetime

from typing import Optional ,Annotated , Literal

from db.models import DeliveryStatus

class Location(BaseModel):
    longitude: float
    latitude: float


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


class RefreshRequest(BaseModel):
    refresh_token: str



class OrderCreate(BaseModel):
    product_id: str
    quantity: int
    address: str



class ShipmentEventIn(BaseModel):
    client_id:UUID
    order_id:UUID
    delivery_address: Location
    api_key:str



class ShipmentEventOut(BaseModel):
    order_id:UUID
    shipment_id:UUID
    pickup_address:Location
    delivery_address:Location
    estimated_delivery: datetime




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