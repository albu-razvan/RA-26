#!/bin/bash
set -e

# Make sure all the resolved symlinks are cleaned up here
trap '
echo "Cleaning up resolved symlinks..."
rm -f ./speech/pynaoqi.tar.gz
' EXIT

echo "Resolving symlinks..."
cp -L ./speech/pynaoqi-symlink.tar.gz ./speech/pynaoqi.tar.gz

# Pepper scripts
echo "Deploying Pepper scripts..."

chmod +x ./audio_forwarder/deploy.sh
./audio_forwarder/deploy.sh

chmod +x ./audio_player/deploy.sh
./audio_player/deploy.sh

# Local services
echo "Starting services..."
docker-compose up
