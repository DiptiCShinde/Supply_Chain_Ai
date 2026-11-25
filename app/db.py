from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _url(raw: str) -> str:
    # Neon gives postgresql://... ; SQLAlchemy needs the psycopg driver name
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql://", 1)
    if raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw


class Base(DeclarativeBase):
    pass


engine = (
    create_engine(_url(settings.database_url), pool_pre_ping=True)
    if settings.database_url
    else None
)
SessionLocal = sessionmaker(bind=engine) if engine else None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
