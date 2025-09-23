# ---------- builder: build wheels ----------
FROM python:3.11-slim AS builder
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --wheel-dir=/wheels -r requirements.txt

# ---------- runtime ----------
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps from wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy only what the server needs (root-level app.py, plus any modules)
COPY app.py ./
# If you have other modules/data at root, copy them too:
# COPY *.py ./            # (optional)
# COPY mypackage/ ./mypackage/  # (optional)

EXPOSE 8000
ENV PORT=8000

# app.py at root exposes FastAPI instance named `app`
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
