#!/usr/bin/env bash
# Build settings.json from base + optional local overrides + optional secrets.
# All inputs are JSONC (JSON-with-comments); output is plain JSON.
#
# Merge order (later overrides earlier):  base ← local ← secrets

set -euo pipefail
cd "$(dirname "$0")"

BASE=settings.base.json
LOCAL=settings.local.json
SECRETS=settings.secrets.json
OUT=settings.json

# Strip JSONC comments (`// ...` and `/* ... */`) while preserving comment-like
# text inside strings. Two-branch regex: branch 1 captures whole strings (and
# re-emits them via $1), branch 2 matches comments outside strings (dropped).
strip_jsonc() {
  perl -0777 -pe '
    s{("(?:\\.|[^"\\])*")|//[^\n]*|/\*[\s\S]*?\*/}
     {defined $1 ? $1 : ""}ges
  ' "$1"
}

inputs=("$BASE")
[ -f "$LOCAL" ]   && inputs+=("$LOCAL")
[ -f "$SECRETS" ] && inputs+=("$SECRETS")

# Materialize each stripped input into a temp file (jq -s --slurp wants real files).
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

tmpfiles=()
for f in "${inputs[@]}"; do
  out="$tmpdir/$(basename "$f")"
  strip_jsonc "$f" > "$out"
  tmpfiles+=("$out")
done

# Recursive object merge across all inputs (arrays are replaced, not concatenated).
jq -s 'reduce .[] as $x ({}; . * $x)' "${tmpfiles[@]}" > "$OUT"

echo "Built $OUT from: ${inputs[*]}"
