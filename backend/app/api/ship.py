from fastapi import APIRouter, HTTPException
from db.schema import ShipmentEventIn
router = APIRouter()



@router.post("/event")
def register_event(e:ShipmentEventIn):
    order_id = e.order_id
    
    delivery_address = e.delivery_address
    api_key = e.api_key

    if not api_key:
        raise HTTPException(status_code=404 , detail="API key not found")
    

    return