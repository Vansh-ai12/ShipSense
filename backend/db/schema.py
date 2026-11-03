from pydantic import BaseModel 

from typing import Optional


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


