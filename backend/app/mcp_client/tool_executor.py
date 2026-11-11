"""
Tool Executor bridge between LangGraph Agent and MCP Client.
Dispatches tool invocations and translates results into graph-ready states.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from app.mcp_client.client import mcp_client

logger = logging.getLogger("app.mcp_client.tool_executor")


class ToolExecutor:
    """
    Executes MCP tools planned by the agent workflow.
    """

    def __init__(self, client=mcp_client):
        self.client = client

    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single MCP tool and measure execution latency."""
        t0 = time.perf_counter()
        result = await self.client.call_tool(tool_name, tool_args)
        latency_ms = int((time.perf_counter() - t0) * 1000)

        return {
            "tool": tool_name,
            "args": tool_args,
            "latency_ms": latency_ms,
            "result": result,
            "success": "error" not in result,
        }

    async def execute_batch(
        self,
        tool_calls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Execute multiple MCP tools concurrently."""
        tasks = [
            self.execute_tool(call["name"], call.get("args", {}))
            for call in tool_calls
        ]
        return await asyncio.gather(*tasks)


tool_executor = ToolExecutor()

