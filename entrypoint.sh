#!/bin/bash
set -e

echo "Starting OutfitAI..."
echo "Memory info:"
free -m 2>/dev/null || cat /proc/meminfo 2>/dev/null | head -5 || echo "(no mem info)"
echo "Disk info:"
df -h /app 2>/dev/null | tail -1 || echo "(no disk info)"
echo "Python version: $(python --version 2>&1)"

# ── Persistent Storage Setup (Hugging Face Buckets) ──────────────────────────
# If the /data bucket is mounted, symlink uploads/ and instance/ there.
# This ensures images and the database persist across restarts.
if [ -d "/data" ]; then
    echo "Found /data bucket. Setting up persistence..."
    
    # 1. Prepare Storage Subdirectories
    mkdir -p /data/uploads /data/instance
    
    # 2. Bridge uploads/ (Items, Avatars, Try-On results)
    if [ -d "/app/uploads" ] && [ ! -L "/app/uploads" ]; then
        echo "Linking /app/uploads to /data/uploads..."
        cp -rn /app/uploads/. /data/uploads/ 2>/dev/null || true
        rm -rf /app/uploads
        ln -s /data/uploads /app/uploads
    fi
    
    # 3. Bridge instance/ (Local DB fallback)
    if [ -d "/app/instance" ] && [ ! -L "/app/instance" ]; then
        echo "Linking /app/instance to /data/instance..."
        cp -rn /app/instance/. /data/instance/ 2>/dev/null || true
        rm -rf /app/instance
        ln -s /data/instance /app/instance
    fi
else
    echo "Warning: /data bucket not found. Files will be ephemeral (deleted on restart)."
fi

# Run Flask migrations
echo "Running database migrations..."
python -m flask db upgrade

# Start Gunicorn
echo "Starting Gunicorn server..."
gunicorn --bind 0.0.0.0:7860 --workers 1 --threads 8 --timeout 180 run:app
