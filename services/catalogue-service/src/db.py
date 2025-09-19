import os, time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB   = os.getenv("POSTGRES_DB", "smartplant")
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PW   = os.getenv("POSTGRES_PASSWORD", "admin123")

DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PW}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db_with_retry(max_attempts: int = 20, sleep_s: float = 1.5) -> None:
    """
    Ensure Postgres is reachable and all tables are created.
    """
    from . import models  # register all model metadata
    for attempt in range(1, max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            time.sleep(sleep_s)
    raise RuntimeError("Database init failed after retries")
