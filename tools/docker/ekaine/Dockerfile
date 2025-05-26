# syntax=docker/dockerfile:1.7-labs
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    jq \
    postgresql \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
COPY tools/docker/ekaine/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN pip install poetry supervisor
COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main

# EXPOSE 8000
# CMD ["poetry", "run", "uvicorn", "ekaine.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]