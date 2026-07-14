#!/bin/bash
# start.sh - Script to start both FastAPI backend and Vite frontend

echo "Starting Backend and Frontend..."

# Get absolute path of current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Start Django backend in a subshell
(
  cd "$SCRIPT_DIR/backend"
  echo "Starting Django backend on port 8000..."
  source ../.venv/bin/activate
  python manage.py runserver 0.0.0.0:8000
) &
BACKEND_PID=$!

# Start Vite frontend in a subshell
(
  cd "$SCRIPT_DIR/frontend"
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  echo "Starting Vite frontend..."
  npm run dev -- --host
) &
FRONTEND_PID=$!

# Function to handle exit
cleanup() {
  echo "Stopping services..."
  kill $BACKEND_PID
  kill $FRONTEND_PID
  exit
}

trap cleanup SIGINT SIGTERM

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop both servers."

wait
