# Multi-stage build for x402-tron-demo
# Stage 1: Build client-web
FROM node:18-alpine AS client-builder

WORKDIR /app/client-web

# Copy package files
COPY client-web/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY client-web/ ./

# Build the application
RUN npm run build

# Stage 2: Final image with Python services and nginx
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Python service code
COPY server/ /app/server/
COPY facilitator/ /app/facilitator/

# Create virtual environment and install Python dependencies
RUN python -m venv /app/.venv && \
    /app/.venv/bin/pip install --upgrade pip && \
    /app/.venv/bin/pip install -r /app/server/requirements.txt && \
    /app/.venv/bin/pip install -r /app/facilitator/requirements.txt

# Copy built client-web from builder stage
COPY --from=client-builder /app/client-web/dist /usr/share/nginx/html

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/nginx.conf

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy startup script
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create logs directory
RUN mkdir -p /app/logs

# Expose ports
# 80: nginx (client-web)
# 8000: server
# 8001: facilitator
EXPOSE 80 8000 8001

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Start services via entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
