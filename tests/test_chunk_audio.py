from app.audio.assistant_recorder import ChunkAudioStore


class SuccessfulConcat:
    def __init__(self) -> None:
        self.commands = []

    def __call__(self, command, **_kwargs):
        self.commands.append(command)
        destination = command[-1]
        assert destination.endswith(".tmp.flac")
        assert command[command.index("-c:a") + 1] == "flac"
        from pathlib import Path
        from types import SimpleNamespace

        Path(destination).write_bytes(b"joined-flac")
        return SimpleNamespace(returncode=0, stderr="")


def test_completed_chunks_excludes_file_still_being_written(settings) -> None:
    store = ChunkAudioStore(settings)
    directory = store.prepare("session-1")
    first = directory / "000000.flac"
    second = directory / "000001.flac"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    assert store.completed_chunks("session-1", capture_active=True) == [first]
    assert store.completed_chunks("session-1", capture_active=False) == [first, second]


def test_single_chunk_is_finalized_atomically(settings) -> None:
    store = ChunkAudioStore(settings)
    chunk = store.prepare("session-1") / "000000.flac"
    chunk.write_bytes(b"fLaC-audio")
    destination = settings.recordings_dir / "session-1.flac"

    assert store.finalize("session-1", destination) is True
    assert destination.read_bytes() == b"fLaC-audio"
    assert store.directory("session-1").exists() is False


def test_multiple_chunks_use_a_flac_temporary_output(settings) -> None:
    runner = SuccessfulConcat()
    store = ChunkAudioStore(settings, runner=runner)
    directory = store.prepare("session-2")
    (directory / "000000.flac").write_bytes(b"one")
    (directory / "000001.flac").write_bytes(b"two")
    destination = settings.recordings_dir / "session-2.flac"

    assert store.finalize("session-2", destination) is True
    assert destination.read_bytes() == b"joined-flac"
    assert len(runner.commands) == 1
