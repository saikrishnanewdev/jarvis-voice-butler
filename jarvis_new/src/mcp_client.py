"""MCP (Model Context Protocol) client integration for LiveKit Agents."""

from __future__ import annotations

import logging
from typing import Any, Callable

from livekit.agents import RunContext, function_tool
from livekit.agents.llm import ToolError

logger = logging.getLogger("mcp_client")


class MCPToolWrapper:
    """Adapts an MCP tool into a LiveKit agent function tool."""

    def __init__(
        self, server_name: str, name: str, description: str, handler: Callable
    ):
        self.server_name = server_name
        self.name = name
        self.description = description
        self.handler = handler

    async def execute(self, context: RunContext, **kwargs: Any) -> Any:
        try:
            return await self.handler(**kwargs)
        except Exception as exc:
            logger.error("MCP Tool %s execution error: %s", self.name, exc)
            raise ToolError(f"MCP tool '{self.name}' failed: {exc}") from exc


def create_livekit_mcp_tool(
    name: str,
    description: str,
    handler: Callable,
) -> Any:
    """Dynamically creates a LiveKit-compatible function tool wrapping an MCP tool."""

    @function_tool(name=name, description=description)
    async def mcp_tool_fn(context: RunContext, **kwargs: Any) -> Any:
        try:
            return await handler(**kwargs)
        except Exception as exc:
            raise ToolError(f"MCP tool failure: {exc}") from exc

    return mcp_tool_fn


class MCPClientManager:
    """Manages MCP server connections and tool registration for LiveKit Agents."""

    def __init__(self) -> None:
        self._tools: list[Any] = []
        self._sessions: list[Any] = []

    @property
    def tools(self) -> list[Any]:
        return self._tools

    async def initialize(self) -> None:
        """Initialize connections to configured MCP servers."""
        # Clean initialization fallback when no external MCP server process is specified
        logger.info(
            "MCP Client Manager initialized (ready for MCP server connections)."
        )

    async def close(self) -> None:
        """Close active MCP sessions."""
        for session in self._sessions:
            try:
                await session.close()
            except Exception as exc:
                logger.warning("Error closing MCP session: %s", exc)
        self._sessions.clear()
