#!/bin/bash
set -e

curl --create-dirs -o $HOME/.postgresql/root.crt 'https://cockroachlabs.cloud/clusters/35b32ca9-ac3c-435b-8f1c-56defee5d735/cert'

# Create necessary directories
mkdir -p static media alembic/versions

# Run migrations if needed
# If using Alembic or other migration tools, uncomment the relevant command
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

python scripts/generate_test_data.py

# Start the application
exec fastapi "$@" 