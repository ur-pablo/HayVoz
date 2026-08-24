# Browser extension

HayVoz includes one WebExtension source in `extensions/web` for Chrome and
Safari. It is a local capture companion, not a page reader: it does not inject
scripts, inspect URLs or DOM content, read cookies/history/storage, or perform
network requests. Its only declared permission is `nativeMessaging`, used to
deliver user-recorded audio to HayVoz on the same device.

## Automatic capture flow

1. Open the HayVoz extension and select **Abrir captura local**.
2. Choose **Elegir pestaña e iniciar**.
3. In the browser's native picker, select the meeting tab and enable its audio.
4. Stop from HayVoz or the browser sharing indicator.
5. The extension sends bounded audio chunks to the local native bridge.
6. The per-user HayVoz service imports the audio, normalizes it to private mono
   16 kHz FLAC, runs local Whisper, and persists the transcript automatically.
7. The capture page reports the session ID and segment count. No manual
   `import-audio` or `transcribe` command is required.

If the native bridge, service, FFmpeg, or model is unavailable, the extension
downloads the captured audio locally as a fallback. It never uploads the audio.
Raw inbox chunks are removed after successful processing and preserved after a
failure so recovery remains possible.

## Chrome development installation

Install a local model and register the native bridge:

```bash
uv run hayvoz model download --model small
uv run hayvoz browser install
```

Then:

1. Open `chrome://extensions`.
2. Enable developer mode.
3. Choose **Load unpacked** and select `extensions/web`.
4. Open HayVoz and confirm that it shows **Procesador local listo**.

The checked-in manifest key provides a stable extension ID. The native-host
manifest allowlists only that ID. The key is public identity material; no private
signing key is stored in the repository. Loading unpacked is suitable for
development; a store release remains a future packaging/review task.

Use `hayvoz browser status` to inspect registration and `hayvoz browser uninstall`
to remove the Chrome native host without deleting sessions or stopping the shared
recovery service.

## Safari development packaging

Safari Web Extensions are delivered inside an Xcode app with a sandboxed native
extension. On a Mac with a current Xcode installation:

```bash
./scripts/package-safari-extension.sh
```

The script generates the ignored `build/safari` project, installs the native
message handler, and adds the `group.com.urpablo.hayvoz` App Group entitlement.
Open the project in Xcode, choose your signing team, confirm the App Group for the
containing app and extension, build the app, and enable the extension in Safari.
The script does not sign, publish, or install anything.

Safari ignores the Chrome host name and routes `sendNativeMessage` to its
containing native extension. That extension writes only to the App Group inbox;
the HayVoz per-user service reads the same local directory.

## Security boundary

- Capture requires a user gesture and the browser's visible native picker.
- Only returned audio tracks enter `MediaRecorder`; video is not encoded or saved.
- Messages use canonical UUID capture directories, chunks capped at 384 KiB, and
  at most 16,384 chunks per capture.
- Chrome uses an allowlisted extension origin; Safari uses a named App Group.
- Inbox directories/files are owner-only where the platform supports it.
- No local HTTP server, TCP listener, page permission, or extension network client
  is introduced.
- Status replies contain only success state, session ID, segment count, or a
  sanitized error—not transcript text, credentials, page metadata, or local paths.

The browser and operating system still mediate capture and can apply their own
policies. A compromised local account/browser remains outside HayVoz's protection.

## Validation status

Protocol validation, automatic processing, origin identity, no-network policy,
and installer helpers are covered by automated tests. Real Chrome and Safari
meeting capture still requires manual browser/hardware validation; browser,
meeting application, and operating-system policies can affect whether tab audio
is available. A successful automated test is not evidence that a particular Meet
session captured audible content.
