import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401


logger = logging.getLogger(__name__)


def _build_engine():
    primary_url = settings.database_url
    primary_kwargs: dict[str, object] = {"pool_pre_ping": True}
    if primary_url.startswith("sqlite"):
        primary_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(primary_url, **primary_kwargs)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return engine
    except OperationalError:
        fallback_url = "sqlite:///./local.db"
        logger.warning("Falling back to local SQLite database at %s", fallback_url)
        return create_engine(
            fallback_url,
            connect_args={"check_same_thread": False},
        )


engine = _build_engine()
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
