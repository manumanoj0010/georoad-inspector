#!/usr/bin/env bash
# Render build script for the backend
set -e

pip install -r requirements.txt

# Ensure upload/data directories exist on persistent disk
mkdir -p "${UPLOAD_DIR:-./uploads}"

echo "Build complete. Model: $(ls -la models/road_damage_best.pt 2>/dev/null || echo 'NOT FOUND')"
