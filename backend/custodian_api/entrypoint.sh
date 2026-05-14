#!/bin/sh
set -e

if [ -n "$CUSTODIAN_DATA_PATH" ] && [ ! -f "$CUSTODIAN_DATA_PATH/customers.parquet" ]; then
    echo "Generating custodian Parquet data in $CUSTODIAN_DATA_PATH ..."
    python /app/scripts/generate_custodian_data.py --out-dir "$CUSTODIAN_DATA_PATH"
fi

exec uvicorn backend.custodian_api.main:app --host 0.0.0.0 --port 8001
