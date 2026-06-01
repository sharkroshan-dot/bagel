#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="/app/data"

echo "==> Downloading ttyd binary..."
# Try downloading from GitHub releases with better fallback
TTYD_URL="https://github.com/tsl0922/ttyd/releases/download/1.7.0/ttyd.x86_64"
TTYD_PATH="/tmp/ttyd"

# Download with verbose output
if ! curl -fL "$TTYD_URL" -o "$TTYD_PATH" 2>&1; then
    echo "==> Failed to download ttyd from $TTYD_URL"
    echo "==> Attempting alternative download..."
    # Fallback: Try a different mirror or version
    curl -fL "https://github.com/tsl0922/ttyd/releases/download/1.6.3/ttyd.x86_64" -o "$TTYD_PATH"
fi

# Verify download is a valid binary
if ! file "$TTYD_PATH" | grep -q "ELF\|executable"; then
    echo "==> Downloaded file is not a valid binary, retrying..."
    rm -f "$TTYD_PATH"
    curl -fL "https://github.com/tsl0922/ttyd/releases/download/1.6.3/ttyd.x86_64" -o "$TTYD_PATH"
fi

chmod +x "$TTYD_PATH"

echo "==> Ensuring data directory exists: $DATA_DIR"
mkdir -p "$DATA_DIR"
chmod 0777 "$DATA_DIR" || true

echo "==> Starting Bagels TUI via ttyd..."
exec "$TTYD_PATH" -p "${PORT:-8080}" -c "${TTYD_CREDENTIALS:-admin:admin}" --watch=false python -m bagels --at "$DATA_DIR"
