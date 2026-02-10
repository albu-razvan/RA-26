#!/bin/bash
set -e

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
    echo "Error: GEMINI_API_KEY is not set. Please export GEMINI_API_KEY first."
    exit 1
fi

# Make sure all the resolved symlinks are cleaned up here
trap '
echo "Cleaning up resolved symlinks..."
rm -f ./pepper/pynaoqi.tar.gz
' EXIT

echo "Resolving symlinks..."
cp -L ./pepper/pynaoqi-symlink.tar.gz ./pepper/pynaoqi.tar.gz

# Pepper scripts
echo "Deploying Pepper scripts..."

chmod +x ./pepper/deploy.sh
./pepper/deploy.sh

# Local services
echo "Starting services..."
docker-compose up
