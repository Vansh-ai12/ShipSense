from fastapi import APIRouter, Depends, HTTPException, status
from db.schema import OrderCreate
from sqlmodel import Session
from services.auth import get_current_user
from db.engine import get_session
from db.models import Order, User
from services.order import create_order
router = APIRouter()


@router.post("/create")
def order_creation(order: OrderCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)):

    return create_order(order, session, user)
