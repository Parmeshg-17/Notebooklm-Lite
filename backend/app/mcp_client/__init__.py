"""
MCP Client package for NotebookLM Lite.
"""

from app.mcp_client.client import MCPClient, mcp_client
from app.mcp_client.tool_executor import ToolExecutor, tool_executor

__all__ = ["MCPClient", "mcp_client", "ToolExecutor", "tool_executor"]

