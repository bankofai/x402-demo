#!/bin/bash

set -e

if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies..."
  npm install
fi

npm run dev
