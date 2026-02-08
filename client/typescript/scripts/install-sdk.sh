#!/bin/bash
# Install @bankofai/x402-tron from tag v0.2.0
# npm doesn't support git subdirectory installs, so we clone, build, and link manually.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SDK_REPO="https://github.com/bankofai/x402-tron.git"
SDK_BRANCH="v0.2.0"
SDK_SUBDIR="typescript/packages/x402"
TARGET_DIR="$CLIENT_DIR/node_modules/@bankofai/x402-tron"

# Skip if already built
if [ -f "$TARGET_DIR/dist/index.js" ]; then
  echo "✅ @bankofai/x402-tron already built, skipping (rm -rf node_modules/@bankofai to force rebuild)"
  exit 0
fi

TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "📦 Cloning x402-tron@${SDK_BRANCH}..."
git clone --depth 1 --branch "$SDK_BRANCH" "$SDK_REPO" "$TEMP_DIR" 2>/dev/null

echo "🔨 Building @bankofai/x402-tron..."
cd "$TEMP_DIR/$SDK_SUBDIR"
npm install --ignore-scripts 2>/dev/null
npx tsc

echo "📁 Installing to node_modules..."
mkdir -p "$TARGET_DIR"
cp -r dist package.json README.md "$TARGET_DIR/" 2>/dev/null || cp -r dist package.json "$TARGET_DIR/"

echo "✅ @bankofai/x402-tron installed from git branch $SDK_BRANCH"
