#!/bin/bash
set -e

echo "==> Downloading ttyd binary..."
curl -L https://github.com/tsl0922/ttyd/releases/download/1.8.3/ttyd.x86_64 -o /tmp/ttyd
chmod +x /tmp/ttyd

echo "==> Starting Bagels TUI via ttyd..."
exec /tmp/ttyd -p ${PORT:-8080} -c ${TTYD_CREDENTIALS:-admin:admin} --watch=false python -m bagels --at /data
