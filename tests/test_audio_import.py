from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.config import Settings
from app.sessions.importer import AudioImportError, AudioImportService
from app.sessions.models import SessionMode, SessionStatus
from app.storage.repository import SessionRepository


def test_import_audio_creates_private_completed_session(
    settings: Settings,
    repository: SessionRepository,
    tmp_path: Path,
) -> None:
    source = tmp_path / "meeting.webm"
    source.write_bytes(b"synthetic-browser-audio")
    calls: list[list[str]] = []

    def runner(command, **_kwargs):
        calls.append(list(command))
        Path(command[-1]).write_bytes(b"fLaC-imported-test")
        return subprocess.CompletedProcess(command, 0, "", "")

    session = AudioImportService(settings, repository, runner).import_audio(
        source,
        title="  Browser meeting  ",
    )

    assert session.title == "Browser meeting"
    assert session.mode is SessionMode.RECORD
    assert session.status is SessionStatus.COMPLETED
    assert session.local_only is True
    assert session.ended_at is not None
    assert session.audio_path.read_bytes() == b"fLaC-imported-test"
    assert calls[0][0] == settings.ffmpeg
    assert calls[0][calls[0].index("-i") + 1] == str(source)
    assert calls[0][calls[0].index("-map_metadata") + 1] == "-1"


def test_failed_import_leaves_no_session_or_partial_audio(
    settings: Settings,
    repository: SessionRepository,
    tmp_path: Path,
) -> None:
    source = tmp_path / "meeting.webm"
    source.write_bytes(b"synthetic-browser-audio")

    def runner(command, **_kwargs):
        Path(command[-1]).write_bytes(b"partial")
        return subprocess.CompletedProcess(command, 1, "", "invalid")

    with pytest.raises(AudioImportError, match="FFmpeg no pudo"):
        AudioImportService(settings, repository, runner).import_audio(
            source,
            title="Failure",
        )

    assert repository.list() == []
    assert list(settings.recordings_dir.iterdir()) == []


@pytest.mark.parametrize("title", ["", "   "])
def test_import_rejects_blank_title(
    settings: Settings,
    repository: SessionRepository,
    tmp_path: Path,
    title: str,
) -> None:
    source = tmp_path / "audio.webm"
    source.write_bytes(b"audio")
    with pytest.raises(AudioImportError, match="título"):
        AudioImportService(settings, repository).import_audio(source, title=title)
