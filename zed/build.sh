#!/bin/sh
cd "$(dirname "$0")"

BASE=settings.base.json
LOCAL=settings.local.json
SECRETS=settings.secrets.json

# Deep merge: base + local overrides + secrets
result=$(cat "$BASE")
[ -f "$LOCAL" ] && result=$(echo "$result" | jq -s '.[0] * .[1]' - "$LOCAL")
[ -f "$SECRETS" ] && result=$(echo "$result" | jq -s '.[0] * .[1]' - "$SECRETS")
echo "$result" > settings.json
echo "Built zed/settings.json"
