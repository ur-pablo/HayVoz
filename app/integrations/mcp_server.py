"""Experimental local read-only MCP server for HayVoz context."""

from __future__ import annotations

import json
from typing import Any

from app.core.session_context import SessionContextService


def create_server(context: SessionContextService) -> Any:
    """Build an MCP server without adding mutation or filesystem tools."""
    try:
        from mcp.server import MCPServer
    except ImportError as error:
        raise RuntimeError(
            "MCP no está instalado. Ejecuta: pip install 'hayvoz[mcp]'"
        ) from error

    server = MCPServer("HayVoz")

    @server.tool(name="hayvoz.list_sessions")
    def list_sessions(limit: int = 100) -> dict[str, Any]:
        """List local HayVoz sessions without local file paths."""
        return {"sessions": context.list_sessions(limit=limit)}

    @server.tool(name="hayvoz.get_session")
    def get_session(session_id: str) -> dict[str, Any]:
        """Read one local HayVoz session."""
        return context.get_session(session_id)

    @server.tool(name="hayvoz.get_transcript")
    def get_transcript(session_id: str) -> dict[str, Any]:
        """Read the persisted transcript segments for one session."""
        return {
            "session_id": session_id,
            "segments": context.get_transcript(session_id),
        }

    @server.tool(name="hayvoz.get_recent_segments")
    def get_recent_segments(session_id: str, limit: int = 20) -> dict[str, Any]:
        """Read recent transcript segments for one session."""
        return {
            "session_id": session_id,
            "segments": context.get_recent_segments(session_id, limit=limit),
        }

    @server.tool(name="hayvoz.get_interview_guide")
    def get_interview_guide(session_id: str) -> dict[str, Any]:
        """Read the copied interview guide for one session, if present."""
        return {
            "session_id": session_id,
            "guide": context.get_interview_guide(session_id),
        }

    @server.tool(name="hayvoz.get_session_context")
    def get_session_context(
        session_id: str, recent_segments: int = 20
    ) -> dict[str, Any]:
        """Read fact-only session context for an external consumer."""
        return context.get_session_context(
            session_id, recent_segments=recent_segments
        )

    return server


def run_stdio(context: SessionContextService) -> None:
    """Run the experimental server over stdin/stdout."""
    server = create_server(context)
    server.run(transport="stdio")


def encode_context(value: dict[str, Any]) -> str:
    """Serialize context for the human-facing CLI command."""
    return json.dumps(value, ensure_ascii=False, indent=2)
