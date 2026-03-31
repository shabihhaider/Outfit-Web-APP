#!/bin/bash
set -e

echo "Starting OutfitAI..."

# Run Flask migrations
echo "Running database migrations..."
python -m flask db upgrade

# Start Gunicorn
echo "Starting Gunicorn server..."
gunicorn --bind 0.0.0.0:7860 --workers 1 --timeout 120 run:app
