#!/bin/bash
set -e

# Create necessary directories
mkdir -p static media

# Run migrations if needed
# If using Alembic or other migration tools, uncomment the relevant command
# alembic upgrade head

# Start the application
exec fastapi "$@" 