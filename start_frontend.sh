#!/usr/bin/env bash
# Start the Vite React development server

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT/frontend"

echo "=========================================================="
echo " Starting Vite React Frontend"
echo " Dev URL: http://localhost:5173"
echo " Proxying API to: http://127.0.0.1:8000"
echo "=========================================================="

npm run dev
