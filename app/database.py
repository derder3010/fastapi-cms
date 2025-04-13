import os
from sqlmodel import SQLModel, Session, create_engine
from contextlib import contextmanager
from typing import Iterator

from app.config import settings

# Create the SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL, 
    echo=False,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

def create_db_and_tables():
    """Create database tables from SQLModel models."""
    try:
        # Import all models here to ensure they're registered with SQLModel
        from app.models import User, Category, Article, Comment
        
        # Create all tables
        SQLModel.metadata.create_all(engine)
        print(f"Database initialized with URL: {settings.DATABASE_URL}")
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        raise


def get_db() -> Iterator[Session]:
    """Dependency function that yields db sessions"""
    with Session(engine) as session:
        yield session


@contextmanager
def get_db_context() -> Session:
    """Context manager for database sessions"""
    session = Session(engine)
    try:
        yield session
    finally:
        session.close() 