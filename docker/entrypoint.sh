#!/bin/bash
set -e

echo "=========================================="
echo "Starting x402-tron-demo services"
echo "=========================================="

# Check if .env file exists
if [ ! -f "/app/.env" ]; then
    echo "ERROR: .env file not found at /app/.env"
    echo "Please mount your .env file with environment variables:"
    echo "  - TRON_PRIVATE_KEY"
    echo "  - PAY_TO_ADDRESS"
    exit 1
fi

echo "✓ Environment file found"

# Load environment variables
export $(grep -v '^#' /app/.env | xargs)

# Validate required environment variables
if [ -z "$TRON_PRIVATE_KEY" ]; then
    echo "ERROR: TRON_PRIVATE_KEY not set in .env"
    exit 1
fi

if [ -z "$PAY_TO_ADDRESS" ]; then
    echo "ERROR: PAY_TO_ADDRESS not set in .env"
    exit 1
fi

echo "✓ Environment variables validated"

# Create logs directory if it doesn't exist
mkdir -p /app/logs

echo ""
echo "Services will be available at:"
echo "  - Client Web:  http://localhost:80"
echo "  - Server API:  http://localhost:8000"
echo "  - Facilitator: http://localhost:8001"
echo ""
echo "Starting services with supervisord..."
echo ""

# Start supervisord to manage all services
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
