import os
import sys
from alembic.config import Config
from alembic import command

def run_migrations():
    """Run Alembic migrations programmatically."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    print("Running database migrations...")
    run_migrations()
    print("Migrations complete!") 