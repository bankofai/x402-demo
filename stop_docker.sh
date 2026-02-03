#!/bin/bash
set -e

echo "=========================================="
echo "Stopping x402-tron-demo"
echo "=========================================="

# Configuration
CONTAINER_NAME="${CONTAINER_NAME:-x402-tron-demo}"

# Check if container exists
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "⚠️  Container ${CONTAINER_NAME} not found"
    exit 0
fi

# Check if container is running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping container..."
    docker stop "${CONTAINER_NAME}"
    echo "✓ Container stopped"
else
    echo "Container is not running"
fi

# Ask if user wants to remove the container
read -p "Remove container? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker rm "${CONTAINER_NAME}"
    echo "✓ Container removed"
fi

echo ""
echo "=========================================="
echo "✅ Done"
echo "=========================================="
