#!/bin/bash
set -e

echo "Starting OutfitAI..."
echo "Python version: $(python --version 2>&1)"

# Temp workspace for image processing (atelier, VTO, preview generation)
mkdir -p /app/uploads /app/instance

# Run Flask migrations
echo "Running database migrations..."
python -m flask db upgrade

# Start Gunicorn
echo "Starting Gunicorn server..."
gunicorn --bind 0.0.0.0:7860 --workers 1 --threads 8 --timeout 180 run:app
