import asyncio
import json
import os
import subprocess
import logging

logger = logging.getLogger("MCPClient")

class MCPClient:
    def __init__(self, command, args, env=None):
        self.command = command
        self.args = args
        self.env = env or os.environ.copy()
        self.process = None

    async def start(self):
        """Start the MCP server process."""
        self.process = await asyncio.create_subprocess_exec(
            self.command, *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env
        )
        
        # Initialize handshake
        await self._send_request("initialize", {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {"name": "eaia-agent", "version": "1.0.0"}
        })
        
        # Wait for initialization response (simplified)
        response = await self._read_response()
        logger.info(f"MCP Initialized: {response}")
        
        await self._send_notification("notifications/initialized", {})

    async def list_tools(self):
        """List available tools from the MCP server."""
        response = await self._send_request("tools/list", {})
        return response.get("result", {}).get("tools", [])

    async def call_tool(self, name, arguments):
        """Call a specific tool on the MCP server."""
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return response.get("result", {}).get("content", [])

    async def _send_request(self, method, params):
        """Send a JSON-RPC request."""
        request_id = 1  # In a real client, manage IDs properly
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        rpc_str = json.dumps(payload) + "\n"
        self.process.stdin.write(rpc_str.encode())
        await self.process.stdin.drain()
        
        return await self._read_response()

    async def _send_notification(self, method, params):
        """Send a JSON-RPC notification."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        rpc_str = json.dumps(payload) + "\n"
        self.process.stdin.write(rpc_str.encode())
        await self.process.stdin.drain()

    async def _read_response(self):
        """Read a JSON-RPC response."""
        line = await self.process.stdout.readline()
        if not line:
            return None
        return json.loads(line.decode())

    async def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
