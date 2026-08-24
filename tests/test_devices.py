from app.audio.devices import (
    AudioDevice,
    parse_alsa_devices,
    parse_avfoundation_devices,
    parse_dshow_devices,
    parse_pulse_devices,
)
from app.ui.doctor import _blackhole_devices, _system_audio_devices


def test_parse_only_audio_devices() -> None:
    output = """
[AVFoundation indev @ 0x1] AVFoundation video devices:
[AVFoundation indev @ 0x1] [0] FaceTime HD Camera
[AVFoundation indev @ 0x1] AVFoundation audio devices:
[AVFoundation indev @ 0x1] [0] Built-in Microphone
[AVFoundation indev @ 0x1] [1] BlackHole 2ch
"""
    devices = parse_avfoundation_devices(output)
    assert [(item.index, item.name) for item in devices] == [
        ("0", "Built-in Microphone"),
        ("1", "BlackHole 2ch"),
    ]


def test_blackhole_detection_is_case_insensitive() -> None:
    devices = [
        AudioDevice(index="0", name="Built-in Microphone"),
        AudioDevice(index="2", name="BLACKHOLE 2ch"),
    ]
    assert _blackhole_devices(devices) == [devices[1]]
    assert _system_audio_devices(devices) == [devices[1]]


def test_parse_windows_and_linux_devices() -> None:
    dshow = '"Microphone Array" (audio)\n"Microphone Array" (audio)'
    pulse = "42 alsa_input.usb-mic module-alsa-card.c s16le 2ch 48000Hz RUNNING"
    alsa = "card 1: USB Audio, device 0: USB Audio [USB Audio]"

    assert parse_dshow_devices(dshow) == [
        AudioDevice(index="Microphone Array", name="Microphone Array")
    ]
    assert parse_pulse_devices(pulse) == [
        AudioDevice(index="alsa_input.usb-mic", name="alsa_input.usb-mic")
    ]
    assert parse_alsa_devices(alsa) == [AudioDevice(index="hw:1,0", name="USB Audio")]
