#!/bin/bash
# Start FastAPI backend + Vite frontend together
# Usage: ./dev.sh

trap 'kill 0' EXIT

echo "Starting FastAPI on :8000..."
cd "$(dirname "$0")"
python -m uvicorn api.main:app --reload --port 8000 &

echo "Starting Vite on :5173..."
cd web && npm run dev &

wait
