#!/bin/bash

# Start script for Core Job Application Agent
# Runs the core agent that orchestrates the workflow

set -e  # Exit on any error

# Set environment variables (no browser needed for core agent)
export PYTHONPATH=/app
export MCP_SERVER_HOST=${MCP_SERVER_HOST:-linkedin-mcp-server}
export MCP_SERVER_PORT=${MCP_SERVER_PORT:-3000}

# Start the Core Job Application Agent
echo "Starting Core Job Application Agent..."
echo "Connecting to MCP Server at $MCP_SERVER_HOST:$MCP_SERVER_PORT"

# Run the agent with error handling
exec python src/main.py
