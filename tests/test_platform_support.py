from app.platform_support import AudioBackend, ffmpeg_audio_input


def test_ffmpeg_input_syntax_is_platform_specific() -> None:
    assert ffmpeg_audio_input("1", AudioBackend.AVFOUNDATION) == [
        "-f",
        "avfoundation",
        "-i",
        ":1",
    ]
    assert ffmpeg_audio_input("Microphone", AudioBackend.DSHOW) == [
        "-f",
        "dshow",
        "-i",
        "audio=Microphone",
    ]
    assert ffmpeg_audio_input("default", AudioBackend.PULSE) == [
        "-f",
        "pulse",
        "-i",
        "default",
    ]
    assert ffmpeg_audio_input("hw:1,0", AudioBackend.ALSA) == [
        "-f",
        "alsa",
        "-i",
        "hw:1,0",
    ]
