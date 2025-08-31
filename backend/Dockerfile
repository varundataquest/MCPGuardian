FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app

EXPOSE ${BACKEND_PORT:-8015}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${BACKEND_PORT:-8015}"]


