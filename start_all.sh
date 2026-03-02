#!/bin/bash
echo "🦅 Launching EAIA Ecosystem..."

# 1. Kill old processes to prevent port conflicts
echo "🧹 Cleaning up old ports..."
pkill -f "eaia/server.py"
lsof -ti:3000 | xargs kill -9 2>/dev/null

# 2. Start Agent Backend (Port 8001)
echo "🧠 Starting Nyx Agent (Port 8001)..."
cd assistant/executive-ai-assistant-main
source .venv/bin/activate
nohup python eaia/server.py > agent.log 2>&1 &
AGENT_PID=$!
echo "   -> Agent PID: $AGENT_PID"
cd ../..

# 3. Start Farfalle Frontend (Port 3000)
echo "🦋 Starting Farfalle Chat (Port 3000)..."
cd scripts/farfalle-main/src/frontend
nohup npm run dev > frontend.log 2>&1 &
FRONT_PID=$!
echo "   -> Frontend PID: $FRONT_PID"
cd ../../../..

echo "✅ System Online!"
echo "   - CRM: http://localhost:8000/crm/nyx"
echo "   - Chat: http://localhost:3000"
echo "   - Agent: http://localhost:8001"
echo ""
echo "logs are being written to agent.log and frontend.log"
