FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

# Node + the @anthropic-ai/claude-code CLI are required by the
# claude-agent-sdk Python wrapper. fund_factsheet_skill and
# fund_lookthrough_skill both shell out to the `claude` CLI via the SDK;
# without it the SDK raises a cryptic "error result: success" at
# runtime, the source returns no_data, and the chain silently drops the
# LLM contribution. Install Node 20 from nodesource (Debian's apt nodejs
# is too old for the Claude Code CLI's >=18 requirement on some
# subcommands), then npm-install the CLI globally so it lands on PATH.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get purge -y curl gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY src /app/src
COPY backend/instrument_api /app/backend/instrument_api

EXPOSE 8003

CMD ["uvicorn", "backend.instrument_api.main:app", "--host", "0.0.0.0", "--port", "8003"]
