#!/bin/bash
set -e

# Create necessary directories
mkdir -p static media alembic/versions

# Run migrations if needed
# If using Alembic or other migration tools, uncomment the relevant command
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

python scripts/generate_test_data.py

# Start the application
exec fastapi "$@" 