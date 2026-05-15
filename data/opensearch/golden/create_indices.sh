#!/bin/sh
# Idempotent: existing indices are skipped, missing ones are created.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"

create_if_missing() {
    name="$1"
    mapping="$2"
    status=$(curl -sS -I -o /dev/null -w "%{http_code}" "$OPENSEARCH_URL/$name")
    if [ "$status" = "200" ]; then
        echo "Index $name already exists, skipping"
    else
        echo "Creating index $name"
        curl -sS -X PUT "$OPENSEARCH_URL/$name" \
             -H "Content-Type: application/json" \
             --data-binary "@$SCRIPT_DIR/$mapping"
        echo
    fi
}

create_if_missing "pms_golden_bond" "pms_golden_bond.index.json"
create_if_missing "pms_golden_equity" "pms_golden_equity.index.json"
create_if_missing "pms_golden_fund" "pms_golden_fund.index.json"
create_if_missing "pms_golden_identifier" "pms_golden_identifier.index.json"
create_if_missing "pms_golden_issuer" "pms_golden_issuer.index.json"
create_if_missing "pms_golden_position" "pms_golden_position.index.json"
