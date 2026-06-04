#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

if [[ -z "${AZURE_OPENAI_ENDPOINT:-}" ]]; then
    echo "Error: AZURE_OPENAI_ENDPOINT is not set. Add it to .env or export it first."
    exit 1
fi

if [[ -z "${AZURE_OPENAI_API_KEY:-}" ]]; then
    echo "Error: AZURE_OPENAI_API_KEY is not set. Add it to .env or export it first."
    exit 1
fi

if [[ -z "${AZURE_OPENAI_DEPLOYMENT:-}" ]]; then
    echo "Error: AZURE_OPENAI_DEPLOYMENT is not set. Add it to .env or export it first."
    exit 1
fi

if [[ -z "${HF_TOKEN:-}" ]]; then
    echo "Error: HF_TOKEN is not set. Add it to .env or export it first."
    exit 1
fi

if [[ -z "${ROBOT_IP:-}" ]]; then
    echo "Error: ROBOT_IP is not set. Add it to .env or export it first."
    exit 1
fi

if [[ -z "${PEPPER_PASS:-}" ]]; then
    echo "Error: PEPPER_PASS is not set. Add it to .env or export it first."
    exit 1
fi

if [[ -z "${COMPUTER_IP:-}" ]]; then
    echo "Error: COMPUTER_IP is not set. Add it to .env or export it first."
    exit 1
fi

if [[ ! -f "$SCRIPT_DIR/controller/games.csv" ]]; then
    echo "Error: controller/games.csv is missing. Create it from controller/games.csv.example."
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
sudo docker compose up
