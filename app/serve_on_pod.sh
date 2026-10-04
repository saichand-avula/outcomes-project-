#!/usr/bin/env bash
# Show the demo UI to other people from the GPU pod: starts the UI and opens a temporary public https link.
# Needs the model server already running on the pod (finetune/scripts/serve_adapters.sh) for the "Try your own" tab; the Examples tab works without it.
#   bash app/serve_on_pod.sh                 # prints the link and a password; Ctrl+C stops both
# The link needs no exposed port: the tunnel tool (cloudflared) connects outwards from the pod.
set -e
cd "$(dirname "$0")/.."
PORT="${PORT:-8080}"
CF="${CF:-/workspace/cloudflared}"
APP_PASSWORD="${APP_PASSWORD:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(9))')}"
export APP_PASSWORD
python3 app/server.py --host 0.0.0.0 --port "$PORT" --llm-url "${LLM_URL:-http://localhost:8000/v1}" --model "${MODEL:-ft3}" --judge-model "${JUDGE:-gemma}" > /tmp/ui.log 2>&1 &
UI=$!
trap 'kill $UI 2>/dev/null' EXIT
for i in $(seq 1 40); do
  curl -s -o /dev/null -u "x:$APP_PASSWORD" "localhost:$PORT/api/config" && break
  kill -0 $UI 2>/dev/null || { echo "UI failed to start:"; cat /tmp/ui.log; exit 1; }
  sleep 1
done
if [ ! -x "$CF" ]; then
  curl -L -o "$CF" https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
  chmod +x "$CF"
fi
echo
echo "UI is up on port $PORT. Password for the page (user name: anything):  $APP_PASSWORD"
echo "The public link appears below (look for https://....trycloudflare.com). Ctrl+C stops everything."
echo
"$CF" tunnel --url "http://localhost:$PORT"
