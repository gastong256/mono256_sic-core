#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || -z "${1// }" ]]; then
  echo "Usage: $0 <url> [requests=200] [concurrency=20]"
  echo "Optional env: BEARER_TOKEN"
  exit 1
fi

URL="$1"
REQUESTS="${2:-200}"
CONCURRENCY="${3:-20}"

if [[ ! "$URL" =~ ^https?:// ]]; then
  echo "Error: URL must start with http:// or https://"
  echo "Received: '$URL'"
  exit 1
fi

RAW_FILE="$(mktemp)"
TIMES_FILE="$(mktemp)"
trap 'rm -f "$RAW_FILE" "$TIMES_FILE"' EXIT

seq "$REQUESTS" | xargs -P "$CONCURRENCY" -I{} bash -lc '
  auth=()
  if [[ -n "${BEARER_TOKEN:-}" ]]; then
    auth=(-H "Authorization: Bearer ${BEARER_TOKEN}")
  fi
  result="$(curl -sS -o /dev/null "${auth[@]}" -w "%{http_code} %{time_total}" "$1" 2>/dev/null || true)"
  if [[ -z "$result" ]]; then
    result="000 0"
  fi
  printf "%s\n" "$result"
' _ "$URL" >> "$RAW_FILE"

awk '{print $2}' "$RAW_FILE" | sort -n > "$TIMES_FILE"
n="$(wc -l < "$TIMES_FILE" | tr -d ' ')"
if [[ "$n" -eq 0 ]]; then
  echo "No samples collected."
  exit 1
fi

success="$(awk '$1 ~ /^2/ {c++} END {print c+0}' "$RAW_FILE")"
avg="$(awk '{sum+=$1} END {printf "%.4f", (NR>0 ? sum/NR : 0)}' "$TIMES_FILE")"
p50_idx="$(( (n + 1) / 2 ))"
p95_idx="$(( (n * 95 + 99) / 100 ))"
p50="$(awk -v idx="$p50_idx" 'NR==idx {printf "%.4f", $1; exit}' "$TIMES_FILE")"
p95="$(awk -v idx="$p95_idx" 'NR==idx {printf "%.4f", $1; exit}' "$TIMES_FILE")"
success_rate="$(awk -v ok="$success" -v total="$n" 'BEGIN {printf "%.2f", (ok * 100.0) / total}')"

echo "Load profile"
echo "  URL: $URL"
echo "  Requests: $REQUESTS"
echo "  Concurrency: $CONCURRENCY"
echo "  Success: $success/$n (${success_rate}%)"
echo "  Avg latency: ${avg}s"
echo "  P50 latency: ${p50}s"
echo "  P95 latency: ${p95}s"
