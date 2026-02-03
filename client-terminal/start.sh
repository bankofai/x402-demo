#!/bin/bash

# Start x402 Facilitator
# This script starts the facilitator service

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Starting x402 Facilitator"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f "../../../.env" ]; then
    echo "Error: .env file not found in project root"
    echo "Please create .env file with required variables:"
    echo "  FACILITATOR_PRIVATE_KEY=<your_private_key>"
    echo "  TRON_NETWORK=<network>"
    echo ""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "../../../.venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run: python -m venv .venv"
    echo ""
    exit 1
fi

# Activate virtual environment
source "../../../.venv/bin/activate"

# Uninstall old version first
echo "Removing old installation..."
python -m ensurepip --upgrade >/dev/null 2>&1 || true
python -m pip uninstall x402-tron -y 2>/dev/null || true
python -m pip uninstall x402 -y 2>/dev/null || true

# Install dependencies
echo "Installing/updating dependencies..."
python -m pip install -e ../../../python/x402[tron]
if [ -f "requirements.txt" ]; then
    python -m pip install -r requirements.txt
fi

# Verify installation
if ! python -c "from x402.clients import X402Client" 2>/dev/null; then
    echo "Error: Failed to import X402Client"
    echo "Please check the installation:"
    echo "  pip list | grep x402-tron"
    echo "  python -c 'import x402; print(x402.__file__)'"
    exit 1
fi

# Start the facilitator
python main.py
