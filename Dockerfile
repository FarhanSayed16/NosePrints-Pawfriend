# NosePrints — production image (PWA + FastAPI + ONNX)
# Build from repo root:
#   docker build -t noseprints .
# Models must exist at backend/models/*.onnx (see docs/DEPLOY.md)

FROM node:20-alpine AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Production PWA talks to same origin (/api/v1)
ENV VITE_API_URL=
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgomp1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY --from=frontend /web/dist /app/frontend_dist

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    SERVE_FRONTEND=true \
    FRONTEND_DIR=/app/frontend_dist \
    DEBUG=false \
    NOSE_DETECTOR_MODEL_PATH=models/nose_detector.onnx \
    EMBEDDING_MODEL_PATH=models/embedding_model.onnx \
    PORT=7860

WORKDIR /app/backend
RUN chmod +x /app/backend/start.sh
EXPOSE 7860
CMD ["/app/backend/start.sh"]
