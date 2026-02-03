#!/bin/bash

# Start x402 Server
# This script starts the protected resource server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Starting x402 Server"
echo "=========================================="
echo ""

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
python -m pip install "x402-tron[tron,fastapi] @ git+https://github.com/open-aibank/x402-tron@fix/opt_cicd"
if [ -f "requirements.txt" ]; then
    python -m pip install -r requirements.txt
fi

# Check installation
echo ""
echo "Checking installation..."
python -m pip list | grep x402-tron
echo ""
python -c "import x402; print('x402 location:', x402.__file__)"
echo ""

# Verify installation
if ! python -c "from x402.server import X402Server" 2>&1; then
    echo ""
    echo "Error: Failed to import X402Server"
    echo "Checking what's available in x402.server module:"
    python -c "import x402.server; print(dir(x402.server))" 2>&1 || echo "Cannot import x402.server at all"
    echo ""
    echo "Checking x402 package structure:"
    python -c "import x402; import os; print(os.listdir(os.path.dirname(x402.__file__)))" 2>&1
    exit 1
fi

echo "Starting server on http://localhost:8000"
echo "Protected endpoint: http://localhost:8000/protected"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the server
python main.py
