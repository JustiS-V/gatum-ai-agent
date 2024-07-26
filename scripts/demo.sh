#!/usr/bin/env bash
# Quick local demo of webhook channels (zendesk + whatsapp) without Telegram token.
set -euo pipefail
BASE="${BASE_URL:-http://localhost:8000}"

post() {
  local channel="$1"
  local client="$2"
  local msg="$3"
  echo ">>> [$channel] $msg"
  payload=$(python3 -c 'import json,sys; print(json.dumps({"client_id":sys.argv[1],"message":sys.argv[2]}))' "$client" "$msg")
  curl -s -X POST "$BASE/channels/$channel/messages" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    | python3 -m json.tool
  echo
}

post zendesk demo-z1 "Як зробити розсилку в Gatum?"
post whatsapp demo-w1 "Хочу поповнити баланс, дайте адресу гаманця"
post zendesk demo-z2 "SMS не доставлено на +380501234567 о 14:30 sender GATUM"
post teams demo-t1 "Скільки коштує ваш тариф зі знижкою?"
post whatsapp demo-w3 "SMPP connection dropped, error timeout bind failed"
post zendesk demo-z9 "asdfgh random question xyz"

echo ">>> Analytics"
curl -s "$BASE/analytics?format=text" | python3 -c "import sys,json; print(json.load(sys.stdin)['report'])"
