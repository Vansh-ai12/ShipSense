from fastapi import APIRouter
from services.pickup import confirm_pickup , report_pickup_failed

router = APIRouter()

@router.post("/")
def confirmPickup():
    
    return