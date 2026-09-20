# Multi-Stage Build: React Vite Frontend + Python Flask Backend
# Stage 1: Build the React Dashboard
FROM node:20-alpine AS build-frontend
WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Backend Server
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (including ffmpeg, glib for OpenCV, and lightweight tesseract)
RUN apt-get update && apt-get install -y --no-install-recommends curl ffmpeg libglib2.0-0 libgomp1 tesseract-ocr libtesseract-dev && rm -rf /var/lib/apt/lists/*

# Install Python requirements with CPU-only PyTorch (lightweight, no CUDA bloat)
COPY ["city flow model/requirements.txt", "./"]
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r requirements.txt

# Pre-cache AI Vision models (YOLOv8n + EasyOCR) into container image so inference is instant
RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False); from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Copy CityFlow Backend code
COPY ["city flow model/", "./cityflow_model/"]

# Copy Vehicle Tracking & Firebase Backend code
COPY ["prototype/", "./prototype/"]

# Copy built React frontend to web static directory
COPY --from=build-frontend /app/frontend/dist ./dist

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV REACT_DIST_DIR=/app/dist
ENV PYTHONPATH="/app/cityflow_model:/app/prototype:${PYTHONPATH}"
ENV PORT=5000


EXPOSE 5000

WORKDIR /app/cityflow_model

# Run with Gunicorn production WSGI server (1 worker, 1 thread to stay strictly within 512MB RAM)
CMD exec gunicorn --workers 1 --threads 1 --bind 0.0.0.0:${PORT:-5000} --timeout 120 server_standalone:app
