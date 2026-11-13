from fastapi import APIRouter , Depends , HTTPException , status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from db.engine import get_session
from db.schema import UserCreate , UserLogin , UserResponse

from db.models import Role , User , RefreshToken

from db.schema import RefreshRequest

from services.auth import hash_refresh_token

from services.auth import DUMMY_HASH, create_access_token, hash_password, verify_password , get_current_user , create_refresh_token

from datetime import datetime, timezone

router = APIRouter()


@router.post("/login")
def login(
    data: UserLogin,
    session: Session = Depends(get_session)
):
    email = data.email.strip().lower()

    user = session.exec(
        select(User).where(User.email == email)
    ).first()

    password_ok = verify_password(
        data.password,
        user.password if user else DUMMY_HASH
    )

    if user is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if user.role != Role.ADMIN or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    access_token = create_access_token(
        str(user.id),
        user.role.value
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


admin = User(
    name="ShipSense Admin",
    email="admin@shipsense.com",
    password=hash_password("your-strong-password"),
    role=Role.ADMIN,
    is_active=True
)

session = get_session()

session.add(admin)
session.commit()