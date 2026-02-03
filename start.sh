#!/bin/bash
set -e

# X402 TRON Demo - Unified Startup Script
# Usage: ./start.sh [server|facilitator|client]

COMPONENT=$1

if [ -z "$COMPONENT" ]; then
    echo "Usage: ./start.sh [server|facilitator|client]"
    echo ""
    echo "Examples:"
    echo "  ./start.sh server       - Start the protected resource server"
    echo "  ./start.sh facilitator  - Start the payment facilitator"
    echo "  ./start.sh client       - Start the terminal client"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo ""
    echo "Please create .env file with:"
    echo "  TRON_PRIVATE_KEY=your_private_key"
    echo "  PAY_TO_ADDRESS=your_tron_address"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

case "$COMPONENT" in
    server)
        echo "=========================================="
        echo "Starting X402 Protected Resource Server"
        echo "=========================================="
        cd server
        python main.py
        ;;
    facilitator)
        echo "=========================================="
        echo "Starting X402 Facilitator"
        echo "=========================================="
        cd facilitator
        python main.py
        ;;
    client)
        echo "=========================================="
        echo "Starting X402 Terminal Client"
        echo "=========================================="
        cd client/terminal
        python main.py
        ;;
    *)
        echo "❌ Unknown component: $COMPONENT"
        echo "Valid options: server, facilitator, client"
        exit 1
        ;;
esac
