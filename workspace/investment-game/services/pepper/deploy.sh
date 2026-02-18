#!/bin/bash
set -e

if [[ -z "${PEPPER_PASS:-}" ]]; then
    echo "Error: PEPPER_PASS is not set. Please export PEPPER_PASS first."
    exit 1
fi

if [[ -z "${COMPUTER_IP:-}" ]]; then
    echo "Error: COMPUTER_IP is not set. Please export COMPUTER_IP first."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PEPPER_USER="nao"
PEPPER_HOST="pepper.local"
PEPPER_PATH="/home/nao"

LOCAL_SCRIPT="$SCRIPT_DIR/audio_handler.py"

echo "Copying audio player script..."
sshpass -p "$PEPPER_PASS" scp "$LOCAL_SCRIPT" "$PEPPER_USER@$PEPPER_HOST:$PEPPER_PATH"

echo "Starting audio player on Pepper..."
sshpass -p "$PEPPER_PASS" ssh "$PEPPER_USER@$PEPPER_HOST" << EOF
pkill -f audio_handler.py 2>/dev/null

export REMOTE_REC_IP="$COMPUTER_IP"

nohup python2.7 $PEPPER_PATH/audio_handler.py > $PEPPER_PATH/audio_handler.log 2>&1 &
EOF
