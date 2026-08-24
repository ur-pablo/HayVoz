# Portability and Language Review

## Decision

Keep Python. A rewrite would not remove the actual portability work: audio APIs,
device naming, process groups, permissions, services, package signing, and
hardware validation.

## Platform adapters

- macOS: FFmpeg AVFoundation; LaunchAgent.
- Windows: FFmpeg DirectShow; Task Scheduler; experimental.
- Linux: FFmpeg PulseAudio or ALSA; systemd user service; experimental.

Windows process recovery queries the local process command through PowerShell
before signaling its private process group. Linux and macOS use POSIX process
groups. Scheduled commands pass the config path as a quoted argument; credentials
remain inside process environment or the owner-only config file.

FFmpeg officially documents AVFoundation, DirectShow, ALSA, and PulseAudio input
devices: <https://ffmpeg.org/ffmpeg-devices.html>.

## Validation status

macOS has real-device validation. Windows/Linux have deterministic command and
parser tests but require hardware matrices before a compatibility promise.

## Rewrite triggers

Revisit a native helper or language change only with measured evidence: packaging
failure, unacceptable resource use, missing secure OS integration, or a capture
API unavailable through FFmpeg. Prefer narrow Rust/Swift/.NET helpers over a full
domain rewrite.
