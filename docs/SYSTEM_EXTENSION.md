# Operating-system Extension

The optional user service runs `hayvoz system run` and performs only local
orphan-session recovery every ten seconds.

```bash
hayvoz system install
hayvoz system status
hayvoz system uninstall
```

It does not record automatically, invoke AI, open a port, accept remote commands,
or require root. The long-lived runtime explicitly discards AI credentials while
loading its settings. The config file path may be embedded in the service
definition; credentials are not.

- macOS uses `~/Library/LaunchAgents`, consistent with Apple's per-user launch
  agent model: <https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html>.
- Windows uses Task Scheduler 2.0, the supported scheduler for modern Windows:
  <https://learn.microsoft.com/en-us/windows/win32/taskschd/about-the-task-scheduler>.
- Linux uses a user-scoped systemd unit under `~/.config/systemd/user`.

Uninstalling the service never deletes recordings or configuration.
