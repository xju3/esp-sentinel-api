#!/bin/sh
# run_api.sh -- run sentinel server api as daemon via .env config
# Usage:
#   ./run_api.sh start [<env-file>]
#   ./run_api.sh stop
#   ./run_api.sh status

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$2"

if [ -z "$ENV_FILE" ]; then
  ENV_FILE="$APP_DIR/.env"
fi

PID_FILE="$APP_DIR/server-api.pid"
LOG_FILE="$APP_DIR/server-api.log"

load_env() {
  if [ -f "$ENV_FILE" ]; then
    set -o allexport
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +o allexport
  fi
}

start() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Already running with pid $(cat "$PID_FILE")"
    return 0
  fi

  echo "Starting Sentinel Server API..."
  cd "$APP_DIR" || exit 1

  load_env

  API_HOST="${API_HOST:-0.0.0.0}"
  API_PORT="${API_PORT:-8000}"

  nohup python -m src >"$LOG_FILE" 2>&1 &
  pid=$!
  echo "$pid" > "$PID_FILE"
  echo "Started on $API_HOST:$API_PORT (pid $pid, log $LOG_FILE)"
}

stop() {
  if [ ! -f "$PID_FILE" ]; then
    echo "No PID file, not running?"
    return 1
  fi

  pid=$(cat "$PID_FILE")
  echo "Stopping pid $pid..."
  kill "$pid" && rm -f "$PID_FILE"
  echo "Stopped."
}

status() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Running pid $(cat "$PID_FILE")"
  else
    echo "Not running"
  fi
}

case "$1" in
  start) start ;;
  stop) stop ;;
  status) status ;;
  *) echo "Usage: $0 {start|stop|status} [<env-file>]" ; exit 2 ;;
esac
