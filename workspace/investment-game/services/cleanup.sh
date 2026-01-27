#!/bin/bash
set -e

# Pepper scripts
echo "Stopping Pepper scripts..."

chmod +x ./audio_forwarder/stop.sh
./audio_forwarder/stop.sh

chmod +x ./audio_player/stop.sh
./audio_player/stop.sh

# Local services
echo "Stopping services..."
docker compose down
