#!/bin/bash

# Start script for LinkedIn MCP Server
# Sets up Xvfb and runs the LinkedIn MCP server
# Supports both direct TCP server and uvicorn if available

set -e  # Exit on any error

# Start Xvfb virtual display
echo "Starting Xvfb virtual display..."
Xvfb :99 -screen 0 1920x1080x24 &

# Wait a moment for Xvfb to start
sleep 2

# Export display variable
export DISPLAY=:99

# Set environment variables
export PYTHONPATH=/app
export CHROME_BIN=/usr/bin/google-chrome
export CHROME_PATH=/usr/bin/google-chrome

# Set MCP server host and port (default to all interfaces in container)
export MCP_SERVER_HOST=${MCP_SERVER_HOST:-0.0.0.0}
export MCP_SERVER_PORT=${MCP_SERVER_PORT:-3000}

echo "Environment: MCP_SERVER_HOST=$MCP_SERVER_HOST, MCP_SERVER_PORT=$MCP_SERVER_PORT"

# Check if we should use uvicorn mode
if [[ "${USE_UVICORN:-false}" == "true" ]]; then
    echo "Starting LinkedIn MCP Server via uvicorn..."
    # Note: Standard MCP uses TCP not HTTP, so this is just if there's a uvicorn adapter
    exec python -m src.linkedin_mcp.linkedin.linkedin_server
else
    echo "Starting LinkedIn MCP Server (TCP mode)..."
    exec python -m src.linkedin_mcp.linkedin.linkedin_server
fi
