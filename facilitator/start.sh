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
if [ ! -f "../.env" ]; then
    echo "Error: .env file not found in project root"
    echo "Please create .env file with required variables:"
    echo "  FACILITATOR_PRIVATE_KEY=<your_private_key>"
    echo "  TRON_NETWORK=<network>"
    echo ""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "../.venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run: python -m venv .venv"
    echo ""
    exit 1
fi

# Activate virtual environment
source "../.venv/bin/activate"

# Uninstall old version first
echo "Removing old installation..."
python -m ensurepip --upgrade >/dev/null 2>&1 || true
python -m pip uninstall x402-tron -y 2>/dev/null || true
python -m pip uninstall x402 -y 2>/dev/null || true

# Install dependencies
echo "Installing/updating dependencies..."
if [ -f "requirements.txt" ]; then
    python -m pip install -r requirements.txt
fi

# Install SDK
python -m pip install "x402-tron[tron,fastapi] @ git+https://github.com/open-aibank/x402-tron@fix/opt_cicd"

# Verify installation
if ! python -c "from x402.facilitator import X402Facilitator" 2>/dev/null; then
    echo "Error: Failed to import X402Facilitator"
    echo "Please check the installation:"
    echo "  pip list | grep x402-tron"
    echo "  python -c 'import x402; print(x402.__file__)'"
    exit 1
fi

echo "Starting facilitator on http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the facilitator
python main.py
