#!/usr/bin/env bash
# Unified launcher for Gemini + HCU AI Desktop Assistant Web UI
# Launches both backend and frontend, and cleans up on exit.

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

# Load GEMINI_API_KEY
if [ -z "$GEMINI_API_KEY" ]; then
    if [ -f "$REPO_ROOT/.env" ]; then
        export $(grep -v '^#' "$REPO_ROOT/.env" | xargs) 2>/dev/null || true
    fi
    if [ -z "$GEMINI_API_KEY" ] && [ -f "$HOME/api_google" ]; then
        export GEMINI_API_KEY="$(cat "$HOME/api_google" | tr -d '\r\n ')"
    fi
fi

export PYTHONPATH="$REPO_ROOT/.site_packages:$REPO_ROOT/sdk/python:$REPO_ROOT:$PYTHONPATH"

cleanup() {
    echo ""
    echo "[*] Shutting down web assistant..."
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    echo "[✓] Shutdown complete."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║   🚀 Gemini + Hybrid Computer Use (HCU) — Web Assistant            ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "[1/2] Starting backend on http://127.0.0.1:8000..."
python3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend health check..."
for i in {1..15}; do
    if curl -s http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
        echo "[✓] Backend is healthy!"
        break
    fi
    sleep 1
done

echo ""
echo "[2/2] Starting frontend on http://localhost:5173..."
cd "$REPO_ROOT/frontend"
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!

echo ""
echo "===================================================================="
echo " ✅ Application is running!"
echo " 👉 Web Interface: http://localhost:5173"
echo " 👉 Backend API   : http://127.0.0.1:8000"
echo " 👉 API Health    : http://127.0.0.1:8000/api/health"
echo "===================================================================="
echo "Press Ctrl+C to stop both servers."
echo ""

wait
