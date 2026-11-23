FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend

RUN useradd --create-home appuser
USER appuser
EXPOSE 8000

# DATABASE_URL and the other settings come from the environment (see .env.example / render.yaml).
# PORT is set by hosts like Render; --proxy-headers + --forwarded-allow-ips let the rate limiter
# see the real client IP behind the host's proxy.
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips="*"
