#!/bin/bash
set -e

if [[ -z "${PEPPER_PASS:-}" ]]; then
    echo "Error: PEPPER_PASS is not set. Please export PEPPER_PASS first."
    exit 1
fi

PEPPER_USER="nao"
PEPPER_HOST="pepper.local"
PEPPER_PATH="/home/nao"

SCRIPT_NAME="audio_handler.py"

echo "Stopping Pepper's audio player..."
sshpass -p "$PEPPER_PASS" ssh "$PEPPER_USER@$PEPPER_HOST" << EOF
pkill -f $SCRIPT_NAME 2>/dev/null || true

if [ -f "$PEPPER_PATH/$SCRIPT_NAME" ]; then
    rm "$PEPPER_PATH/$SCRIPT_NAME"
fi
EOF
