# Operating-system Extension

The optional user service runs `hayvoz system run`. Every two seconds it performs
local orphan-session recovery and processes completed browser captures from an
owner-only inbox.

```bash
hayvoz system install
hayvoz system status
hayvoz system uninstall
```

It does not start recording, invoke an AI provider, open a port, accept remote
commands, or require root. Browser processing imports audio and runs the local
Whisper model only after the user finishes an explicit extension capture. The
long-lived runtime explicitly discards AI credentials while loading its settings.
The config file path may be embedded in the service definition; credentials are
not.

- macOS uses `~/Library/LaunchAgents`, consistent with Apple's per-user launch
  agent model: <https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html>.
- Windows uses Task Scheduler 2.0, the supported scheduler for modern Windows:
  <https://learn.microsoft.com/en-us/windows/win32/taskschd/about-the-task-scheduler>.
- Linux uses a user-scoped systemd unit under `~/.config/systemd/user`.

Uninstalling the service never deletes recordings or configuration.
