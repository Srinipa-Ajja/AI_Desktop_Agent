#!/usr/bin/env bash
# Start the FastAPI backend for Gemini + HCU AI Desktop Assistant

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Resolve display and desktop bus if missing
export DISPLAY="${DISPLAY:-:0}"
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ] && [ -e "/run/user/$(id -u)/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
fi
if [ -z "$XAUTHORITY" ]; then
    if [ -f "/run/user/$(id -u)/gdm/Xauthority" ]; then
        export XAUTHORITY="/run/user/$(id -u)/gdm/Xauthority"
    elif [ -f "$HOME/.Xauthority" ]; then
        export XAUTHORITY="$HOME/.Xauthority"
    fi
fi

# Load GEMINI_API_KEY if not already in env
if [ -z "$GEMINI_API_KEY" ]; then
    if [ -f "$REPO_ROOT/.env" ]; then
        export $(grep -v '^#' "$REPO_ROOT/.env" | xargs) 2>/dev/null || true
    fi
    if [ -z "$GEMINI_API_KEY" ] && [ -f "$HOME/api_google" ]; then
        export GEMINI_API_KEY="$(cat "$HOME/api_google" | tr -d '\r\n ')"
    fi
fi

export PYTHONPATH="$REPO_ROOT/.site_packages:$REPO_ROOT/sdk/python:$REPO_ROOT:$PYTHONPATH"

echo "=========================================================="
echo " Starting Gemini + HCU AI Desktop Assistant Backend"
echo " Host: http://127.0.0.1:8000"
echo " Display: $DISPLAY"
echo " DBus: $DBUS_SESSION_BUS_ADDRESS"
echo "=========================================================="

python3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
