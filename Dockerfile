# Dockerfile unifie - Backend API + Frontend statique en un seul service
# Utilise pour le deploiement sur Render (free tier = 1 service)

# ── Stage 1: Build Frontend ──
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ── Stage 2: Backend + serve static ──
FROM python:3.12-slim

WORKDIR /app

# Deps systeme
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le backend
COPY backend/ /app/backend/

# Copier le frontend builde
COPY --from=frontend-builder /app/frontend/dist /app/static

ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
