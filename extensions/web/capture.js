"use strict";

const startButton = document.querySelector("#start");
const stopButton = document.querySelector("#stop");
const statusText = document.querySelector("#status");
const indicator = document.querySelector("#indicator");
const titleInput = document.querySelector("#title");

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

function finishRecording() {
  if (!recorder || chunks.length === 0) {
    releaseSource();
    setStatus("La captura terminó sin audio utilizable.");
    startButton.disabled = false;
    stopButton.disabled = true;
    return;
  }

  const title = titleInput.value.trim() || "Reunión desde navegador";
  const extension = recorder.mimeType.includes("mp4") ? "m4a" : "webm";
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const baseName = `${safeBaseName(title)}-${stamp}`;
  const audioFile = `${baseName}.${extension}`;
  const audioBlob = new Blob(chunks, { type: recorder.mimeType });
  const receipt = {
    schema_version: 1,
    source: "hayvoz-browser-extension",
    captured_at: new Date().toISOString(),
    title,
    recording_file: audioFile,
    network_requests: 0,
  };

  downloadBlob(audioBlob, audioFile);
  downloadBlob(
    new Blob([`${JSON.stringify(receipt, null, 2)}\n`], {
      type: "application/json",
    }),
    `${baseName}.json`,
  );
  releaseSource();
  chunks = [];
  recorder = null;
  startButton.disabled = false;
  stopButton.disabled = true;
  setStatus("Captura finalizada. Los archivos se descargaron localmente.");
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
