#!/bin/sh
# Run this once before your first `docker compose up`
# Creates the persistent data directories Docker needs for bind mounts

mkdir -p data/uploads data/tokens

# jobs.json must exist as a file (not a directory) before the container starts
if [ ! -f data/jobs.json ]; then
  echo "[]" > data/jobs.json
fi

echo "✓ data/ directory initialised — ready to run: docker compose up --build"
