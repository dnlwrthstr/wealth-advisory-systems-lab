FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY src /app/src
COPY backend/custodian_api /app/backend/custodian_api

# Parquet data is mounted at runtime via CUSTODIAN_DATA_PATH.
# When the env var is absent the service falls back to in-memory fixture data.
VOLUME ["/data/custodian"]

EXPOSE 8001

CMD ["uvicorn", "backend.custodian_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
