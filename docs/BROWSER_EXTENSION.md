# Browser extension

HayVoz includes one permission-free WebExtension source in `extensions/web` for
Chrome and Safari. It is a local capture companion, not a page reader: it does
not inject scripts, inspect URLs or DOM content, read cookies/history, or perform
network requests.

## Capture flow

1. Open the HayVoz extension and select **Abrir captura local**.
2. Choose **Elegir pestaña e iniciar**.
3. In the browser's native picker, select the meeting tab and enable its audio.
4. Stop from HayVoz or the browser sharing indicator.
5. The extension downloads the audio and a minimal JSON receipt locally.
6. Import and transcribe the audio:

```bash
hayvoz import-audio ~/Downloads/meeting.webm --title "Private meeting"
hayvoz transcribe SESSION_ID --language es
hayvoz transcript SESSION_ID
```

During import, FFmpeg removes embedded source metadata and normalizes the audio
to private mono 16 kHz FLAC before the session is recorded in SQLite.

The receipt contains only a user-entered title, capture time, recording filename,
and schema/source identifiers. It intentionally excludes the page URL, hostname,
browser language, participants, meeting content, cookies, account data, and HayVoz
session identifiers. HayVoz does not import the receipt automatically.

## Chrome development installation

1. Open `chrome://extensions`.
2. Enable developer mode.
3. Choose **Load unpacked** and select `extensions/web`.

Chrome displays the native sharing prompt on every capture. Choose the meeting
tab and enable tab audio. Loading unpacked is suitable for development; a store
release remains a future packaging/review task.

## Safari development packaging

Safari Web Extensions are delivered inside an Xcode app project. On a Mac with a
current Xcode installation:

```bash
./scripts/package-safari-extension.sh
```

The generated project is written under ignored `build/safari`. Open it in Xcode,
select your signing team, build the containing app, enable its extension in
Safari settings, and grant capture only when Safari asks. The script does not
sign, publish, or install anything.

## Validation status

The shared manifest and privacy invariants are covered by automated tests. Chrome
and Safari meeting capture still require manual browser/hardware validation;
browser, meeting application, and operating-system policies can affect whether
tab audio is available. Never claim a capture succeeded without checking the
downloaded file.
