FROM python:3.12-slim

# Install uv natively (not via pip — per mentor feedback)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV PYTHONPATH=/app
ENV UV_SYSTEM_PYTHON=1

COPY requirements.txt .
RUN uv pip install -r requirements.txt

COPY . .

CMD ["python", "run_ingest.py"]
