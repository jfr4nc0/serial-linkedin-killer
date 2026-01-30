#!/bin/bash

# Start script for Core Job Application Agent API
# Runs the FastAPI server that orchestrates workflows

set -e  # Exit on any error

# Set environment variables (no browser needed for core agent)
export PYTHONPATH=/app
export MCP_SERVER_HOST=${MCP_SERVER_HOST:-linkedin-mcp-server}
export MCP_SERVER_PORT=${MCP_SERVER_PORT:-3000}

# API config
API_HOST=${API_HOST:-0.0.0.0}
API_PORT=${API_PORT:-8080}

SERVER_PID=""

cleanup() {
    echo "Shutting down Core Agent API..."
    if [ -n "$SERVER_PID" ]; then
        # Send SIGTERM to the entire process group so child threads/subprocesses die too
        kill -- -"$SERVER_PID" 2>/dev/null || true
        # Wait briefly for graceful shutdown
        sleep 2
        # Force kill if still alive
        kill -9 -- -"$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# Start the Core Agent API
echo "Starting Core Agent API..."
echo "Connecting to MCP Server at $MCP_SERVER_HOST:$MCP_SERVER_PORT"
echo "Connecting to Kafka at ${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"
echo "API listening on $API_HOST:$API_PORT"

# Run in a new process group so we can kill all children
set -m
uvicorn src.core.api.app:app --host "$API_HOST" --port "$API_PORT" &
SERVER_PID=$!
wait "$SERVER_PID"
