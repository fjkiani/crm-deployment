import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.utils import DB_ENABLED

load_dotenv()

POSTGRES_USER = os.environ.get("POSTGRES_USER") or "postgres"
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD") or "password"
POSTGRES_HOST = os.environ.get("POSTGRES_HOST") or "localhost"
POSTGRES_PORT = os.environ.get("POSTGRES_PORT") or "5432"
POSTGRES_DB = os.environ.get("POSTGRES_DB") or "postgres"

DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


def create_connection_string():
    return DATABASE_URL


if DB_ENABLED:
    engine = create_engine(create_connection_string())
else:
    # Lightweight SQLite fallback so imports work without Postgres
    engine = create_engine("sqlite+pysqlite:///:memory:")


def get_session():
    with Session(engine) as session:
        yield session
