#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"

echo "Creating index pms_golden_bond"
curl -sS -X PUT "$OPENSEARCH_URL/pms_golden_bond" -H "Content-Type: application/json" --data-binary "@$SCRIPT_DIR/pms_golden_bond.index.json"
echo

echo "Creating index pms_golden_equity"
curl -sS -X PUT "$OPENSEARCH_URL/pms_golden_equity" -H "Content-Type: application/json" --data-binary "@$SCRIPT_DIR/pms_golden_equity.index.json"
echo

echo "Creating index pms_golden_fund"
curl -sS -X PUT "$OPENSEARCH_URL/pms_golden_fund" -H "Content-Type: application/json" --data-binary "@$SCRIPT_DIR/pms_golden_fund.index.json"
echo

echo "Creating index pms_golden_identifier"
curl -sS -X PUT "$OPENSEARCH_URL/pms_golden_identifier" -H "Content-Type: application/json" --data-binary "@$SCRIPT_DIR/pms_golden_identifier.index.json"
echo

echo "Creating index pms_golden_position"
curl -sS -X PUT "$OPENSEARCH_URL/pms_golden_position" -H "Content-Type: application/json" --data-binary "@$SCRIPT_DIR/pms_golden_position.index.json"
echo

