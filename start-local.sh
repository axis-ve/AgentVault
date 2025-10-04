#!/bin/bash

# AgentVault MCP - Local Development Startup Script
# This script starts all components needed for local development

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ASCII Art Banner
echo -e "${BLUE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     █████╗  ██████╗ ███████╗███╗   ██╗████████╗            ║
║    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝            ║
║    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║               ║
║    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║               ║
║    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║               ║
║    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝               ║
║                                                              ║
║         VAULT MCP - Local Development Environment           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}[INFO]${NC} Project root: $PROJECT_ROOT"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[WARN]${NC} .env file not found. Creating from .env.local template..."
    if [ -f ".env.local" ]; then
        cp .env.local .env
        echo -e "${GREEN}[SUCCESS]${NC} Created .env file. Please edit it and add your ENCRYPT_KEY."
        echo ""
        echo -e "${YELLOW}[ACTION REQUIRED]${NC} Generate encryption key:"
        echo "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        echo ""
        echo -e "${YELLOW}[ACTION REQUIRED]${NC} Add the generated key to .env as ENCRYPT_KEY="
        echo ""
        exit 1
    else
        echo -e "${RED}[ERROR]${NC} .env.local template not found!"
        exit 1
    fi
fi

# Check if ENCRYPT_KEY is set
if ! grep -q "^ENCRYPT_KEY=.\+" .env; then
    echo -e "${RED}[ERROR]${NC} ENCRYPT_KEY not set in .env file!"
    echo ""
    echo -e "${YELLOW}[ACTION]${NC} Generate encryption key:"
    echo "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    echo ""
    echo "Then add it to .env: ENCRYPT_KEY=<your-generated-key>"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

echo -e "${GREEN}[✓]${NC} Environment configuration loaded"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}[WARN]${NC} Virtual environment not found. Creating..."
    python3 -m venv .venv
    echo -e "${GREEN}[✓]${NC} Virtual environment created"
fi

# Activate virtual environment
echo -e "${BLUE}[INFO]${NC} Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies
echo -e "${BLUE}[INFO]${NC} Installing/updating Python dependencies..."
pip install -q --upgrade pip
pip install -q -e '.[ui]' 2>/dev/null || pip install -e .

# Install dashboard backend dependencies
echo -e "${BLUE}[INFO]${NC} Installing dashboard backend dependencies..."
cd dashboard/backend
pip install -q -r requirements.txt
cd "$PROJECT_ROOT"

echo -e "${GREEN}[✓]${NC} All dependencies installed"

# Run database migrations
echo -e "${BLUE}[INFO]${NC} Running database migrations..."
python -m agentvault_mcp.db.cli upgrade
echo -e "${GREEN}[✓]${NC} Database migrations complete"

# Check if database was created
if [ -f "agentvault.db" ]; then
    echo -e "${GREEN}[✓]${NC} Database initialized: agentvault.db"
else
    echo -e "${YELLOW}[WARN]${NC} Database file not found at expected location"
fi

# Create PID directory for process management
mkdir -p .pids

# Function to start backend
start_backend() {
    echo -e "${BLUE}[INFO]${NC} Starting Dashboard Backend API..."
    cd "$PROJECT_ROOT/dashboard/backend"

    # Use integrated version if exists, otherwise use mock
    if [ -f "main_integrated.py" ]; then
        nohup python main_integrated.py > "$PROJECT_ROOT/.pids/backend.log" 2>&1 &
        echo $! > "$PROJECT_ROOT/.pids/backend.pid"
        echo -e "${GREEN}[✓]${NC} Backend started (Integrated with MCP)"
    else
        nohup python main.py > "$PROJECT_ROOT/.pids/backend.log" 2>&1 &
        echo $! > "$PROJECT_ROOT/.pids/backend.pid"
        echo -e "${GREEN}[✓]${NC} Backend started (Mock mode)"
    fi

    cd "$PROJECT_ROOT"
}

# Function to start frontend
start_frontend() {
    echo -e "${BLUE}[INFO]${NC} Checking Dashboard Frontend..."
    cd "$PROJECT_ROOT/dashboard"

    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}[WARN]${NC} Node modules not found. Running npm install..."
        npm install
    fi

    echo -e "${BLUE}[INFO]${NC} Starting Dashboard Frontend..."
    nohup npm start > "$PROJECT_ROOT/.pids/frontend.log" 2>&1 &
    echo $! > "$PROJECT_ROOT/.pids/frontend.pid"
    echo -e "${GREEN}[✓]${NC} Frontend starting (this takes ~30 seconds)..."

    cd "$PROJECT_ROOT"
}

# Start components
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Starting AgentVault Components${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

start_backend
sleep 3  # Give backend time to start

start_frontend
sleep 2

# Wait for services to be ready
echo ""
echo -e "${BLUE}[INFO]${NC} Waiting for services to be ready..."
sleep 8

# Check if services are running
backend_running=false
frontend_running=false

if [ -f ".pids/backend.pid" ]; then
    if ps -p $(cat .pids/backend.pid) > /dev/null 2>&1; then
        backend_running=true
    fi
fi

if [ -f ".pids/frontend.pid" ]; then
    if ps -p $(cat .pids/frontend.pid) > /dev/null 2>&1; then
        frontend_running=true
    fi
fi

# Print status
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Service Status${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$backend_running" = true ]; then
    echo -e "${GREEN}[✓]${NC} Backend API:    http://localhost:8000"
    echo -e "    Docs:           http://localhost:8000/docs"
    echo -e "    Health:         http://localhost:8000/health"
else
    echo -e "${RED}[✗]${NC} Backend API:    Failed to start (check .pids/backend.log)"
fi

if [ "$frontend_running" = true ]; then
    echo -e "${GREEN}[✓]${NC} Frontend:       http://localhost:3000 ${YELLOW}(starting...)${NC}"
else
    echo -e "${YELLOW}[~]${NC} Frontend:       Starting... (wait 30 seconds)"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Quick Start${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "1. ${GREEN}Dashboard${NC}: Open http://localhost:3000 in your browser"
echo -e "   - Login with: demo@agentvault.com / demo123"
echo ""
echo -e "2. ${GREEN}Create an Agent${NC}:"
echo -e "   - Go to Agents page"
echo -e "   - Click 'Create Agent'"
echo -e "   - Enter name and description"
echo ""
echo -e "3. ${GREEN}CLI Commands${NC}:"
echo -e "   - List wallets:  ${BLUE}agentvault list-wallets${NC}"
echo -e "   - Check balance: ${BLUE}agentvault balance <agent-id>${NC}"
echo -e "   - Send ETH:      ${BLUE}agentvault send <agent-id> <to> <amount>${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Logs${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "- Backend:  ${BLUE}tail -f .pids/backend.log${NC}"
echo -e "- Frontend: ${BLUE}tail -f .pids/frontend.log${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Stop All Services${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Run: ${BLUE}./stop-local.sh${NC}"
echo ""
echo -e "${GREEN}[SUCCESS]${NC} AgentVault is starting! Check http://localhost:3000 in ~30 seconds"
echo ""

# Keep script running and show logs
echo -e "${BLUE}[INFO]${NC} Following backend logs (Ctrl+C to exit, services will keep running)..."
echo ""
tail -f .pids/backend.log 2>/dev/null || echo "Waiting for logs..."
