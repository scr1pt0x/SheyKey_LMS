#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="/opt/homebrew/opt/python@3.12/bin:/opt/homebrew/opt/postgresql@16/bin:/opt/homebrew/opt/node@20/bin:$PATH"
export PYTHONPATH="$ROOT"

# Activate venv if it exists
[ -f "$ROOT/.venv/bin/activate" ] && source "$ROOT/.venv/bin/activate"

# Free ports
for PORT in 8000 3000; do
  PID=$(lsof -ti :"$PORT" 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo "→ Освобождаю порт $PORT (PID $PID)"
    kill "$PID" 2>/dev/null || true
    sleep 0.5
  fi
done

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  Islamic Finance LMS — dev mode         │"
echo "│  Backend:  http://localhost:8000/api/docs│"
echo "│  Frontend: http://localhost:3000         │"
echo "│  Ctrl+C — остановить всё                │"
echo "└─────────────────────────────────────────┘"
echo ""

# Start backend in background, pipe output with prefix
(cd "$ROOT/backend" && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 \
  | while IFS= read -r line; do echo "[api]  $line"; done) &
BACKEND_PID=$!

# Wait for backend to be ready
echo "→ Запуск API..."
for i in $(seq 1 20); do
  sleep 0.5
  curl -s http://localhost:8000/api/health > /dev/null 2>&1 && break
done
echo "✓ API готов"

# Start frontend in background
(cd "$ROOT/frontend" && npm run dev 2>&1 \
  | while IFS= read -r line; do echo "[web]  $line"; done) &
FRONTEND_PID=$!

# On Ctrl+C kill both
cleanup() {
  echo ""
  echo "→ Останавливаю сервисы..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  lsof -ti :8000 | xargs kill 2>/dev/null || true
  lsof -ti :3000 | xargs kill 2>/dev/null || true
  echo "✓ Готово"
  exit 0
}
trap cleanup INT TERM

# Keep running and show output
wait
