import os
from sqlmodel import SQLModel, Session, create_engine
from contextlib import contextmanager
from typing import Iterator, Generator

from app.config import settings

# Create the SQLAlchemy engine with the appropriate configuration
engine = create_engine(
    settings.DATABASE_URL, 
    echo=False,
    # SQLite specific connect argument, ignored for other database types
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

def create_db_and_tables():
    """Create database tables from SQLModel models."""
    try:
        # Create all tables based on imported models
        SQLModel.metadata.create_all(engine)
        
        # Identify database type from URL
        # SQLAlchemy officially supports these dialects
        db_url = settings.DATABASE_URL.lower()
        if db_url.startswith("sqlite"):
            db_type = "SQLite"
        elif db_url.startswith("postgresql") or "cockroach" in db_url:
            db_type = "PostgreSQL/CockroachDB"
        elif db_url.startswith("mysql"):
            db_type = "MySQL/MariaDB"
        elif db_url.startswith("oracle"):
            db_type = "Oracle"
        elif db_url.startswith("mssql") or "sqlserver" in db_url:
            db_type = "Microsoft SQL Server"
        elif db_url.startswith("firebird"):
            db_type = "Firebird"
        # Other database types through external dialects
        elif db_url.startswith("mongodb"):
            db_type = "MongoDB (external)"
        elif db_url.startswith("cassandra"):
            db_type = "Cassandra (external)"
        elif db_url.startswith("db2"):
            db_type = "IBM DB2"
        elif db_url.startswith("sap") or "hana" in db_url:
            db_type = "SAP HANA"
        elif "snowflake" in db_url:
            db_type = "Snowflake"
        elif "redshift" in db_url:
            db_type = "Amazon Redshift"
        elif "bigquery" in db_url:
            db_type = "Google BigQuery"
        else:
            db_type = "Unknown"
            
        print(f"Database initialized successfully. Type: {db_type}")
    except Exception as e:
        print(f"Error creating database tables: {str(e)}")
        raise


def get_db() -> Iterator[Session]:
    """
    Dependency function that yields database sessions.
    Used with FastAPI dependency injection system.
    """
    with Session(engine) as session:
        yield session


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Used for standalone scripts or when dependency injection is not available.
    """
    session = Session(engine)
    try:
        yield session
    finally:
        session.close() 