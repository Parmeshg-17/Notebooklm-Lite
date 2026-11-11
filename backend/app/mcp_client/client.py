"""
Model Context Protocol (MCP) Client for NotebookLM Lite.
Interacts with the local MCP Server to discover and invoke tools with high fidelity.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from app.mcp_server.server import notebooklm_mcp_server

logger = logging.getLogger("app.mcp_client.client")


class MCPClient:
    """
    Client interface for calling MCP tools.
    Supports in-process async tool execution with standardized error handling.
    """

    def __init__(self, server=notebooklm_mcp_server):
        self.server = server

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """List all tools exposed by the MCP server."""
        tools = await self.server.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description,
            }
            for t in tools
        ]

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool by name and return parsed JSON result dictionary.
        """
        try:
            res = await self.server.call_tool(name, arguments)
            if res.is_error:
                error_msg = res.content[0].text if res.content else "Unknown MCP error"
                return {"error": error_msg, "status": "failed"}

            if res.content and len(res.content) > 0:
                raw_text = res.content[0].text
                try:
                    return json.loads(raw_text)
                except json.JSONDecodeError:
                    return {"result": raw_text, "status": "success"}

            return {"status": "success", "data": None}
        except Exception as e:
            logger.error(f"Error calling MCP tool '{name}': {e}", exc_info=True)
            return {"error": str(e), "status": "failed"}


mcp_client = MCPClient()

