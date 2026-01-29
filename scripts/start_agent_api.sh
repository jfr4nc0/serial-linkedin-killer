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

# Start the Core Agent API
echo "Starting Core Agent API..."
echo "Connecting to MCP Server at $MCP_SERVER_HOST:$MCP_SERVER_PORT"
echo "Connecting to Kafka at ${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"
echo "API listening on $API_HOST:$API_PORT"

exec uvicorn src.core.api.app:app --host "$API_HOST" --port "$API_PORT"
