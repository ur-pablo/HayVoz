from app.audio.recorder import FFmpegRecorder, system_audio_path_for


def test_dual_source_command_uses_one_process_and_two_outputs(settings) -> None:
    recorder = FFmpegRecorder(settings)
    audio_path = settings.recordings_dir / "session.flac"

    command = recorder.build_command(audio_path, "0", system_device="1")

    assert command.count(settings.ffmpeg) == 1
    assert command.count("avfoundation") == 2
    assert command.count(":0") == 1
    assert command.count(":1") == 1
    assert command.count("flac") == 2
    assert str(audio_path) in command
    assert str(system_audio_path_for(audio_path)) in command
    assert command.index(str(audio_path)) < command.index(
        str(system_audio_path_for(audio_path))
    )


def test_single_source_command_does_not_create_system_output(settings) -> None:
    recorder = FFmpegRecorder(settings)
    audio_path = settings.recordings_dir / "session.flac"

    command = recorder.build_command(audio_path, "0")

    assert command.count("avfoundation") == 1
    assert str(system_audio_path_for(audio_path)) not in command
