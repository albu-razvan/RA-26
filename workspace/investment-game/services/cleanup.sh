#!/bin/bash
set -e

# Pepper scripts
echo "Stopping Pepper scripts..."

chmod +x ./pepper/stop.sh
./pepper/stop.sh

# Local services
echo "Stopping services..."
docker compose down
