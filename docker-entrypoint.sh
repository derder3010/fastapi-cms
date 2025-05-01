#!/bin/bash
set -e

# Create necessary directories
mkdir -p static media alembic/versions $HOME/.postgresql

# Handle root certificate from environment variable
if [ -n "$ROOT_CERT" ]; then
  echo "$ROOT_CERT" > /etc/ssl/custom-certs/root.crt
  chmod 644 /etc/ssl/custom-certs/root.crt
  ln -sf /etc/ssl/custom-certs/root.crt $HOME/.postgresql/root.crt
  update-ca-certificates
  echo "SSL certificate configured from environment variable"
else
  echo "WARNING: ROOT_CERT environment variable not set, SSL certificate not configured"
fi

# Run migrations if needed
# If using Alembic or other migration tools, uncomment the relevant command
# alembic revision --autogenerate -m "Initial migration"
# alembic upgrade head

# python scripts/generate_test_data.py

# Start the application
exec fastapi "$@" 