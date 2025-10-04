#!/bin/bash

# AgentVault MCP - Stop Local Development Services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}[INFO]${NC} Stopping AgentVault services..."

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file=".pids/${service_name}.pid"

    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${BLUE}[INFO]${NC} Stopping ${service_name} (PID: $pid)..."
            kill $pid 2>/dev/null || true
            sleep 2

            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "${YELLOW}[WARN]${NC} Force killing ${service_name}..."
                kill -9 $pid 2>/dev/null || true
            fi

            echo -e "${GREEN}[✓]${NC} Stopped ${service_name}"
        else
            echo -e "${YELLOW}[WARN]${NC} ${service_name} not running (stale PID file)"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}[WARN]${NC} No PID file for ${service_name}"
    fi
}

# Stop backend
stop_service "backend"

# Stop frontend
stop_service "frontend"

# Clean up log files (optional)
if [ "$1" = "--clean" ]; then
    echo -e "${BLUE}[INFO]${NC} Cleaning up log files..."
    rm -f .pids/*.log
    echo -e "${GREEN}[✓]${NC} Log files cleaned"
fi

echo ""
echo -e "${GREEN}[SUCCESS]${NC} All AgentVault services stopped"
echo ""
