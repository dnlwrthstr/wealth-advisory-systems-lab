FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY src /app/src
COPY backend/profile_api /app/backend/profile_api

EXPOSE 8002

CMD ["uvicorn", "backend.profile_api.main:app", "--host", "0.0.0.0", "--port", "8002"]
