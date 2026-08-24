from __future__ import annotations

import pytest

from app.core.session_context import SessionContextService
from app.integrations.mcp_server import create_server
from app.sessions.service import SessionService
from app.storage.transcript_repository import TranscriptRepository
from tests.fakes import FakeRecorder

mcp = pytest.importorskip("mcp")


@pytest.mark.anyio
async def test_mcp_exposes_only_read_tools(settings, repository) -> None:
    context = SessionContextService(
        settings,
        repository,
        TranscriptRepository(repository.database),
    )
    session = SessionService(settings, repository, FakeRecorder()).start(
        title="MCP test", local_only=True
    )
    SessionService(settings, repository, FakeRecorder()).stop()
    server = create_server(context)

    async with mcp.Client(server) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        result = await client.call_tool(
            "hayvoz.get_session", {"session_id": session.id}
        )

    assert names == {
        "hayvoz.list_sessions",
        "hayvoz.get_session",
        "hayvoz.get_transcript",
        "hayvoz.get_recent_segments",
        "hayvoz.get_interview_guide",
        "hayvoz.get_session_context",
    }
    assert result.is_error is False
    assert result.structured_content["title"] == "MCP test"
