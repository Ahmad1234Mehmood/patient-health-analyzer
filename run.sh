#!/usr/bin/env bash
# One-command setup + launch (macOS / Linux).  Usage:  bash run.sh
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || { echo "Python 3 not found. Install Python 3.10+ first."; exit 1; }
command -v npm  >/dev/null || { echo "Node.js/npm not found. Install Node 18+ first."; exit 1; }

echo "==> Backend: virtual environment + dependencies"
if [ ! -d backend/.venv ]; then "$PY" -m venv backend/.venv; fi
backend/.venv/bin/python -m pip install --quiet --upgrade pip
backend/.venv/bin/python -m pip install --quiet -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env

echo "==> Frontend: npm install"
if [ ! -d frontend/node_modules ]; then (cd frontend && npm install --no-audit --no-fund); fi

echo "==> Starting backend on http://localhost:5000 and frontend on http://localhost:5173  (Ctrl+C stops both)"
(cd backend && ../backend/.venv/bin/python run.py) &
BACK=$!
(cd frontend && npm run dev -- --host 127.0.0.1) &
FRONT=$!
trap 'kill $BACK $FRONT 2>/dev/null; exit 0' INT TERM
wait


