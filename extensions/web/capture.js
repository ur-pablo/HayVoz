"use strict";

const startButton = document.querySelector("#start");
const stopButton = document.querySelector("#stop");
const statusText = document.querySelector("#status");
const indicator = document.querySelector("#indicator");
const titleInput = document.querySelector("#title");
const HOST_NAME = "com.urpablo.hayvoz";
const UPLOAD_CHUNK_BYTES = 384 * 1024;

let sourceStream = null;
let recorder = null;
let chunks = [];

const MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/mp4",
  "audio/webm",
];

function setStatus(message, active = false) {
  statusText.textContent = message;
  indicator.classList.toggle("active", active);
}

function selectedMimeType() {
  return MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function normalizedMimeType(value) {
  const normalized = value.toLowerCase();
  if (normalized.startsWith("audio/mp4")) return "audio/mp4";
  if (normalized.includes("codecs=opus")) return "audio/webm;codecs=opus";
  return "audio/webm";
}

function safeBaseName(value) {
  const normalized = value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
  return normalized.slice(0, 60) || "hayvoz-browser";
}

function downloadBlob(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function releaseSource() {
  if (sourceStream) {
    sourceStream.getTracks().forEach((track) => track.stop());
  }
  sourceStream = null;
}

function nativeMessage(message) {
  const accept = (response) => {
    if (!response || response.ok === false) {
      throw new Error(response?.error || "NATIVE_HOST_ERROR");
    }
    return response;
  };
  const browserApi = globalThis.browser;
  if (browserApi?.runtime?.sendNativeMessage) {
    try {
      return Promise.resolve(
        browserApi.runtime.sendNativeMessage(HOST_NAME, message),
      ).then(accept);
    } catch (_error) {
      return Promise.reject(new Error("NATIVE_HOST_UNAVAILABLE"));
    }
  }
  const chromeApi = globalThis.chrome;
  return new Promise((resolve, reject) => {
    if (!chromeApi?.runtime?.sendNativeMessage) {
      reject(new Error("NATIVE_MESSAGING_UNAVAILABLE"));
      return;
    }
    let settled = false;
    const succeed = (response) => {
      if (settled) return;
      settled = true;
      const lastError = chromeApi.runtime.lastError;
      if (lastError) {
        reject(new Error("NATIVE_HOST_UNAVAILABLE"));
      } else {
        try {
          resolve(accept(response));
        } catch (error) {
          reject(error);
        }
      }
    };
    try {
      const pending = chromeApi.runtime.sendNativeMessage(
        HOST_NAME,
        message,
        succeed,
      );
      if (pending && typeof pending.then === "function") {
        pending.then(succeed).catch(() => {
          if (!settled) {
            settled = true;
            reject(new Error("NATIVE_HOST_UNAVAILABLE"));
          }
        });
      }
    } catch (_error) {
      reject(new Error("NATIVE_HOST_UNAVAILABLE"));
    }
  });
}

function newCaptureId() {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0"));
  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex.slice(6, 8).join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10).join("")}`;
}

function encodeBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  return btoa(binary);
}

function delay(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function uploadAndTranscribe(audioBlob, title) {
  const captureId = newCaptureId();
  await nativeMessage({
    type: "start",
    capture_id: captureId,
    title,
    mime_type: normalizedMimeType(audioBlob.type),
  });
  const buffer = await audioBlob.arrayBuffer();
  let sequence = 0;
  for (let offset = 0; offset < buffer.byteLength; offset += UPLOAD_CHUNK_BYTES) {
    const part = buffer.slice(offset, offset + UPLOAD_CHUNK_BYTES);
    await nativeMessage({
      type: "chunk",
      capture_id: captureId,
      sequence,
      data: encodeBase64(part),
    });
    sequence += 1;
    setStatus(`Guardando audio localmente… ${Math.min(offset + part.byteLength, buffer.byteLength)} / ${buffer.byteLength} bytes`);
  }
  await nativeMessage({
    type: "finish",
    capture_id: captureId,
    chunk_count: sequence,
  });
  setStatus("Audio guardado. Transcribiendo offline…", true);
  for (let attempt = 0; attempt < 3600; attempt += 1) {
    const result = await nativeMessage({ type: "status", capture_id: captureId });
    if (result.status === "completed") return result;
    if (result.status === "failed") throw new Error(result.error || "TRANSCRIPTION_FAILED");
    await delay(2000);
  }
  throw new Error("TRANSCRIPTION_TIMEOUT");
}

function downloadFallback(audioBlob, title) {
  const extension = audioBlob.type.includes("mp4") ? "m4a" : "webm";
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  downloadBlob(audioBlob, `${safeBaseName(title)}-${stamp}.${extension}`);
}

async function finishRecording() {
  if (!recorder || chunks.length === 0) {
    releaseSource();
    setStatus("La captura terminó sin audio utilizable.");
    startButton.disabled = false;
    stopButton.disabled = true;
    return;
  }

  const title = titleInput.value.trim() || "Reunión desde navegador";
  const audioBlob = new Blob(chunks, { type: recorder.mimeType });
  releaseSource();
  try {
    setStatus("Enviando al procesador local…", true);
    const result = await uploadAndTranscribe(audioBlob, title);
    setStatus(
      `Transcripción guardada automáticamente. Sesión ${result.session_id} · ${result.segment_count} segmentos.`,
    );
  } catch (_error) {
    downloadFallback(audioBlob, title);
    setStatus(
      "El puente local no completó la transcripción. Se descargó el audio como respaldo.",
    );
  } finally {
    chunks = [];
    recorder = null;
    startButton.disabled = false;
    stopButton.disabled = true;
  }
}

async function startRecording() {
  startButton.disabled = true;
  titleInput.disabled = true;
  setStatus("Esperando que elijas una pestaña…");
  try {
    sourceStream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: true,
    });
    const audioTracks = sourceStream.getAudioTracks();
    if (audioTracks.length === 0) {
      releaseSource();
      throw new Error("NO_AUDIO_TRACK");
    }
    const audioStream = new MediaStream(audioTracks);
    const mimeType = selectedMimeType();
    recorder = mimeType
      ? new MediaRecorder(audioStream, { mimeType })
      : new MediaRecorder(audioStream);
    chunks = [];
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    });
    recorder.addEventListener("stop", finishRecording, { once: true });
    sourceStream.getVideoTracks()[0].addEventListener(
      "ended",
      () => {
        if (recorder && recorder.state !== "inactive") recorder.stop();
      },
      { once: true },
    );
    recorder.start(1000);
    stopButton.disabled = false;
    setStatus("Grabando localmente. Detén aquí o desde el navegador.", true);
  } catch (error) {
    releaseSource();
    startButton.disabled = false;
    stopButton.disabled = true;
    const detail =
      error instanceof Error && error.message === "NO_AUDIO_TRACK"
        ? "La fuente elegida no compartió audio. Reintenta y activa compartir audio."
        : "Captura cancelada o no autorizada. No se guardó nada.";
    setStatus(detail);
  } finally {
    titleInput.disabled = false;
  }
}

function stopRecording() {
  stopButton.disabled = true;
  if (recorder && recorder.state !== "inactive") {
    recorder.stop();
  }
}

startButton.addEventListener("click", startRecording);
stopButton.addEventListener("click", stopRecording);

nativeMessage({ type: "ping" })
  .then(() => setStatus("Procesador local listo. La transcripción será automática."))
  .catch(() =>
    setStatus("Puente local no disponible. Ejecuta: hayvoz browser install"),
  );
