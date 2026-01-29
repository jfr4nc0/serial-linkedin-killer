#!/bin/bash

# Start script for LinkedIn MCP Server
# Works both locally (real display) and in Docker (Xvfb)

set -e

export PYTHONPATH=${PYTHONPATH:-$(cd "$(dirname "$0")/.." && pwd)}
export MCP_SERVER_HOST=${MCP_SERVER_HOST:-0.0.0.0}
export MCP_SERVER_PORT=${MCP_SERVER_PORT:-3000}

XVFB_PID=""

cleanup() {
    if [ -n "$XVFB_PID" ]; then
        kill "$XVFB_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# Start Xvfb only if no display is available and Xvfb exists
if [ -z "$DISPLAY" ]; then
    if command -v Xvfb &> /dev/null; then
        echo "Starting Xvfb virtual display..."
        Xvfb :99 -screen 0 1920x1080x24 &
        XVFB_PID=$!
        sleep 2
        export DISPLAY=:99
    else
        echo "Warning: No display and Xvfb not found. Browser may fail in headless mode."
    fi
fi

echo "MCP Server: $MCP_SERVER_HOST:$MCP_SERVER_PORT"

exec python -m src.linkedin_mcp.linkedin.linkedin_server
