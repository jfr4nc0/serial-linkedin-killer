#!/usr/bin/env python3
"""
LinkedIn Job Application Agent - Terminal Client
Entry point for the command-line interface.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from cli.client import JobApplicationCLI


def start_linkedin_mcp_server():
    """Start the LinkedIn MCP HTTP server as a background process."""
    print("🚀 Starting LinkedIn MCP HTTP server...")
    
    # Change to the project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if server is already running
    try:
        import requests
        response = requests.get("http://localhost:8000/mcp", timeout=2)
        if response.status_code < 500:
            print("✅ LinkedIn MCP server already running")
            return
    except:
        pass  # Server not running, need to start it
    
    # Start the server in background
    cmd = [
        sys.executable,  # Use current Python interpreter
        "-m", "src.linkedin_mcp.linkedin.linkedin_server",
        "--http",
        "--host", "localhost",
        "--port", "8000",
    ]
    
    print(f"📡 Starting MCP server: {' '.join(cmd)}")
    
    # Start server as background process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Combine stderr with stdout
        text=True
    )
    
    # Wait for server to start (max 10 seconds)
    for i in range(10):
        try:
            import requests
            response = requests.get("http://localhost:8000/mcp", timeout=1)
            if response.status_code < 500:
                print(f"✅ LinkedIn MCP server started successfully on http://localhost:8000")
                return process
        except:
            time.sleep(1)
            print(f"⏳ Waiting for server to start... ({i+1}/10)")
    
    print("❌ Failed to start LinkedIn MCP server")
    # Get process output regardless of whether it's still running
    try:
        stdout, stderr = process.communicate(timeout=1)
        print(f"Server output: {stdout}")
        if stderr:
            print(f"Server errors: {stderr}")
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        print(f"Server output (after kill): {stdout}")
        if stderr:
            print(f"Server errors (after kill): {stderr}")
    sys.exit(1)


def main():
    """Main entry point for the CLI application."""
    # Start LinkedIn MCP server first
    start_linkedin_mcp_server()
    
    # Start CLI
    cli = JobApplicationCLI()
    cli.run()


if __name__ == "__main__":
    main()
