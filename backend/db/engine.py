from sqlmodel import create_engine, Session, SQLModel

DATABASE_URL = "postgresql://shipsense:shipsense@localhost:5432/shipsense"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session