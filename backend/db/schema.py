from pydantic import BaseModel

from uuid import UUID

from datetime import datetime

from typing import Optional ,Annotated , Literal


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
    user_id: str
    product_id: str
    quantity: int
    price: float
    address: str
    has_paid: bool







class PickupLocation(BaseModel):
    longitude: float
    latitude: float


class OrderCreatedEvent(BaseModel):
    event_type: Literal["OrderCreated"]

    order_id: UUID

    product_id: UUID
    created_at: datetime

    pickup_location: PickupLocation


class AgentAssignedEvent(BaseModel):
    event_type: Literal["AgentAssigned"]
    order_id: UUID
    agent_id: str
