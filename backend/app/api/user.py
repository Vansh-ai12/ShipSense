from fastapi import APIRouter , Depends , HTTPException , status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from db.engine import get_session
from db.schema import UserCreate , UserLogin , UserResponse

from db.models import Role , User

from services.auth import DUMMY_HASH, create_access_token, hash_password, verify_password

router = APIRouter()

@router.post("/login")
def login(data: UserLogin, session: Session = Depends(get_session)):
    email = data.email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()

    password_ok = verify_password(data.password, user.password if user else DUMMY_HASH)

    if user is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(str(user.id), user.role.value)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, session: Session = Depends(get_session)):
    email = data.email.strip().lower()

    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=email,
        password=hash_password(data.password),  
        role=Role.USER,                         
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:                      
        session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    session.refresh(user)
    return user

@router.delete("/{user_id}/logout")
def logout(user_id: str):
    return {"message": f"Logout endpoint for user {user_id}"}   