"""Typer command-line interface."""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from app import __version__
from app.analysis.models import AnalysisType
from app.analysis.service import AnalysisService, AnalysisServiceError
from app.assistant.service import (
    AssistantService,
    AssistantServiceError,
    AssistantSnapshot,
)
from app.audio.assistant_recorder import AssistantRecorder
from app.audio.devices import list_audio_devices
from app.audio.recorder import FFmpegRecorder
from app.browser.integration import (
    BrowserIntegrationError,
    BrowserIntegrationManager,
)
from app.browser.processor import BrowserProcessor
from app.config import Settings
from app.i18n import assistant_aliases, assistant_term
from app.llm.factory import create_provider
from app.llm.provider import LLMProvider, LLMProviderError
from app.logging_config import configure_logging
from app.sessions.guide import InterviewGuideStore
from app.sessions.importer import AudioImportError, AudioImportService
from app.sessions.models import SessionMode
from app.sessions.service import SessionService, SessionServiceError
from app.storage.analysis_repository import AnalysisRepository
from app.storage.assistant_repository import AssistantRepository
from app.storage.database import Database
from app.storage.repository import (
    ActiveSessionError,
    SessionNotFoundError,
    SessionRepository,
)
from app.storage.transcript_repository import TranscriptRepository
from app.system_service import SystemServiceError, SystemServiceManager
from app.transcription.json_store import TranscriptJsonStore
from app.transcription.model_manager import ModelManagerError, WhisperModelManager
from app.transcription.models import Speaker, WhisperModelName
from app.transcription.service import TranscriptionService, TranscriptionServiceError
from app.transcription.transcriber import FasterWhisperTranscriber
from app.ui.doctor import CheckLevel, run_doctor

app = typer.Typer(
    name="hayvoz",
    help="Grabador local y asistente privado para entrevistas.",
    no_args_is_help=True,
)
model_app = typer.Typer(help="Administra modelos Whisper locales.")
system_app = typer.Typer(help="Integra HayVoz como servicio privado del usuario.")
browser_app = typer.Typer(help="Integra la extensión con la transcripción local.")
app.add_typer(model_app, name="model")
app.add_typer(system_app, name="system")
app.add_typer(browser_app, name="browser")
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Muestra la versión instalada y termina.",
        ),
    ] = False,
) -> None:
    """Configura las opciones globales de HayVoz."""


@dataclass(frozen=True, slots=True)
class Runtime:
    settings: Settings
    database: Database
    sessions: SessionRepository
    session_service: SessionService


def _runtime(*, load_ai_credentials: bool = True) -> Runtime:
    settings = Settings.from_env(load_ai_credentials=load_ai_credentials)
    settings.ensure_directories()
    configure_logging(settings.logs_dir)
    database = Database(settings.database_path)
    database.initialize()
    repository = SessionRepository(database)
    return Runtime(
        settings=settings,
        database=database,
        sessions=repository,
        session_service=SessionService(
            settings,
            repository,
            FFmpegRecorder(settings),
            AssistantRecorder(settings),
        ),
    )


def _transcription_service(
    runtime: Runtime,
    model: WhisperModelName,
) -> TranscriptionService:
    return TranscriptionService(
        runtime.sessions,
        TranscriptRepository(runtime.database),
        TranscriptJsonStore(runtime.settings),
        FasterWhisperTranscriber(runtime.settings, model),
    )


def _analysis_service(
    runtime: Runtime,
    provider: LLMProvider | None = None,
) -> AnalysisService:
    return AnalysisService(
        runtime.sessions,
        TranscriptRepository(runtime.database),
        AnalysisRepository(runtime.database),
        provider,
    )


def _system_service() -> SystemServiceManager:
    settings = Settings.from_env(load_ai_credentials=False)
    return SystemServiceManager(Path(sys.argv[0]), settings.config_path)


def _browser_integration() -> BrowserIntegrationManager:
    settings = Settings.from_env(load_ai_credentials=False)
    suffix = ".exe" if os.name == "nt" else ""
    native_executable = Path(sys.argv[0]).resolve().with_name(f"hayvoz-native{suffix}")
    return BrowserIntegrationManager(native_executable, settings.config_path)


@system_app.command("install")
def system_install() -> None:
    """Instala el agente local para el usuario actual; no abre puertos."""
    try:
        path = _system_service().install()
    except SystemServiceError as error:
        console.print(f"[red]No se pudo instalar el servicio:[/red] {error}")
        raise typer.Exit(1) from error
    console.print(f"[green]Servicio de usuario instalado[/green]: {path}")


@system_app.command("uninstall")
def system_uninstall() -> None:
    """Elimina la integración del usuario sin borrar sus datos."""
    _system_service().uninstall()
    console.print("[green]Servicio de usuario desinstalado.[/green]")


@system_app.command("status")
def system_status() -> None:
    """Muestra si la integración está instalada."""
    status = _system_service().status()
    color = "green" if status.installed else "yellow"
    console.print(f"[{color}]{status.detail}[/{color}]")


@system_app.command("run", hidden=True)
def system_run(
    config: Annotated[
        Path | None,
        typer.Option("--config", hidden=True),
    ] = None,
) -> None:
    """Ejecuta el agente local sin sockets ni grabación automática."""
    if config is not None:
        os.environ["HAYVOZ_CONFIG_FILE"] = str(config.expanduser().resolve())
    runtime = _runtime(load_ai_credentials=False)
    browser_processor = BrowserProcessor(
        runtime.settings,
        runtime.database,
        runtime.sessions,
    )
    stop_event = threading.Event()

    def request_stop(_number: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    while not stop_event.is_set():
        runtime.session_service.recover_orphans()
        browser_processor.process_pending()
        stop_event.wait(2.0)


@browser_app.command("install")
def browser_install() -> None:
    """Registra el puente nativo y activa el procesador privado del usuario."""
    integration = _browser_integration()
    service = _system_service()
    try:
        manifests = integration.install()
        service_path = service.install()
    except (BrowserIntegrationError, SystemServiceError) as error:
        integration.uninstall()
        console.print(f"[red]No se pudo instalar el puente:[/red] {error}")
        raise typer.Exit(1) from error
    console.print("[green]Puente privado del navegador instalado.[/green]")
    for manifest in manifests:
        console.print(f"Manifest: {manifest}")
    console.print(f"Procesador local: {service_path}")


@browser_app.command("uninstall")
def browser_uninstall() -> None:
    """Desregistra el host del navegador sin borrar sesiones ni transcripciones."""
    _browser_integration().uninstall()
    console.print("[green]Puente del navegador desinstalado.[/green]")
    console.print("Los datos privados y el servicio de recuperación se conservaron.")


@browser_app.command("status")
def browser_status() -> None:
    """Muestra si Chrome tiene registrado el host nativo local."""
    status = _browser_integration().status()
    if not status.installed:
        console.print("[yellow]Puente del navegador no instalado.[/yellow]")
        return
    console.print("[green]Puente del navegador instalado.[/green]")
    for manifest in status.manifests:
        console.print(str(manifest))


@app.command("uninstall")
def uninstall_command() -> None:
    """Elimina integraciones y servicios; conserva todos los datos privados."""
    _browser_integration().uninstall()
    _system_service().uninstall()
    console.print("[green]Integraciones de HayVoz desinstaladas.[/green]")
    console.print("Sesiones, transcripciones, modelos y configuración se conservaron.")


@app.command()
def doctor(
    skip_mic_check: Annotated[
        bool,
        typer.Option("--skip-mic-check", help="No intenta una captura breve."),
    ] = False,
) -> None:
    """Diagnostica el sistema sin instalar ni modificar dependencias."""
    runtime = _runtime()
    checks = run_doctor(runtime.settings, probe_mic=not skip_mic_check)
    table = Table(title="HayVoz — doctor")
    table.add_column("Estado")
    table.add_column("Componente")
    table.add_column("Detalle")
    table.add_column("Sugerencia")
    labels = {
        CheckLevel.OK: "[green]OK[/green]",
        CheckLevel.WARNING: "[yellow]WARN[/yellow]",
        CheckLevel.ERROR: "[red]ERROR[/red]",
    }
    for check in checks:
        table.add_row(labels[check.level], check.name, check.detail, check.suggestion)
    console.print(table)
    if any(check.level is CheckLevel.ERROR for check in checks):
        raise typer.Exit(1)


@app.command()
def devices() -> None:
    """Lista entradas de audio visibles para ffmpeg en este sistema."""
    runtime = _runtime()
    try:
        found = list_audio_devices(
            runtime.settings.ffmpeg, backend=runtime.settings.audio_backend
        )
    except RuntimeError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1) from error
    if not found:
        console.print("[yellow]No se detectaron dispositivos de audio.[/yellow]")
        raise typer.Exit(1)
    table = Table(title="Dispositivos de audio")
    table.add_column("Índice")
    table.add_column("Nombre")
    for device in found:
        table.add_row(device.index, device.name)
    console.print(table)


@app.command()
def start(
    title: Annotated[str, typer.Option("--title", help="Título de la sesión.")],
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            case_sensitive=False,
            help="record o el alias localizado de Assistant.",
        ),
    ] = SessionMode.RECORD.value,
    device: Annotated[
        str | None,
        typer.Option("--device", help="Índice mostrado por 'hayvoz devices'."),
    ] = None,
    system_device: Annotated[
        str | None,
        typer.Option(
            "--system-device",
            help="Entrada virtual del audio remoto; solo record mode.",
        ),
    ] = None,
    local_only: Annotated[
        bool,
        typer.Option(
            "--local-only", help="Prohíbe futuras llamadas al proveedor de IA."
        ),
    ] = False,
    guide: Annotated[
        Path | None,
        typer.Option("--guide", help="Cuestionario Markdown de la entrevista."),
    ] = None,
    confirm_send: Annotated[
        bool,
        typer.Option(
            "--confirm-send",
            help="Autoriza envíos de texto periódicos en Assistant mode.",
        ),
    ] = False,
    chunk_seconds: Annotated[
        int | None,
        typer.Option("--chunk-seconds", min=10, max=20, help="Duración de chunks."),
    ] = None,
    analysis_interval: Annotated[
        int | None,
        typer.Option(
            "--analysis-interval",
            min=10,
            help="Segundos mínimos de audio nuevo entre llamadas.",
        ),
    ] = None,
    last_segments: Annotated[
        int | None,
        typer.Option("--last-segments", min=1, max=200, help="Rolling context."),
    ] = None,
) -> None:
    """Inicia una grabación de micrófono en segundo plano."""
    runtime = _runtime()
    service = runtime.session_service
    try:
        selected_mode = _parse_session_mode(mode)
        session = service.start(
            title=title,
            mode=selected_mode,
            device=device,
            system_device=system_device,
            local_only=local_only,
            guide=guide,
            allow_external=confirm_send,
            assistant_chunk_seconds=chunk_seconds,
            assistant_analysis_interval_seconds=analysis_interval,
            assistant_last_segments=last_segments,
        )
    except (SessionServiceError, ActiveSessionError) as error:
        console.print(f"[red]No se pudo iniciar:[/red] {error}")
        raise typer.Exit(1) from error
    console.print(f"[green]Grabación iniciada[/green] — sesión {session.id}")
    console.print(f"Audio: {session.audio_path}")
    if session.system_audio_path:
        console.print(f"Audio sistema: {session.system_audio_path}")
    if session.guide_path:
        console.print(f"Guía local: {session.guide_path}")
    if session.mode is SessionMode.ASSISTANT:
        localized_assistant = assistant_term(runtime.settings.language)
        console.print(
            f"{localized_assistant}: chunks de {session.assistant_chunk_seconds}s, "
            "análisis cada "
            f"{session.assistant_analysis_interval_seconds}s, contexto de "
            f"{session.assistant_last_segments} segmentos."
        )
        if session.local_only:
            console.print(
                f"{localized_assistant} local-only: transcribe incrementalmente sin IA."
            )
        else:
            alias = localized_assistant.casefold()
            console.print(f"Consulta sugerencias con: hayvoz {alias} {session.id}")
            if not runtime.settings.ai_api_key or not runtime.settings.ai_model:
                console.print(
                    "[yellow]El proveedor de IA no está configurado: la grabación y la "
                    "transcripción continuarán, pero no habrá sugerencias.[/yellow]"
                )
    console.print("Finaliza con: hayvoz stop")


@app.command()
def stop() -> None:
    """Finaliza de forma segura la grabación activa."""
    service = _runtime().session_service
    try:
        session = service.stop()
    except SessionServiceError as error:
        console.print(f"[red]No se pudo detener:[/red] {error}")
        raise typer.Exit(1) from error
    color = "green" if session.status.value == "completed" else "yellow"
    console.print(f"[{color}]Sesión {session.status.value}[/{color}] — {session.id}")
    console.print(f"Audio: {session.audio_path}")
    if session.system_audio_path:
        console.print(f"Audio sistema: {session.system_audio_path}")


@app.command("sessions")
def sessions_command(
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
) -> None:
    """Lista las sesiones locales más recientes."""
    service = _runtime().session_service
    sessions = service.list_sessions(limit=limit)
    if not sessions:
        console.print("No hay sesiones.")
        return
    table = Table(title="Sesiones")
    table.add_column("ID")
    table.add_column("Título")
    table.add_column("Estado")
    table.add_column("Modo")
    table.add_column("Inicio")
    table.add_column("Audio")
    table.add_column("Audio sistema")
    for session in sessions:
        table.add_row(
            session.id,
            session.title,
            session.status.value,
            session.mode.value,
            session.started_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            if session.started_at
            else "—",
            str(session.audio_path),
            str(session.system_audio_path) if session.system_audio_path else "—",
        )
    console.print(table)


@app.command("import-audio")
def import_audio_command(
    source: Annotated[
        Path,
        typer.Argument(help="Audio local exportado por la extensión u otra fuente."),
    ],
    title: Annotated[
        str,
        typer.Option("--title", help="Título privado de la sesión importada."),
    ],
) -> None:
    """Convierte un audio local a FLAC y lo registra sin acceso de red."""
    runtime = _runtime(load_ai_credentials=False)
    try:
        session = AudioImportService(
            runtime.settings,
            runtime.sessions,
        ).import_audio(source, title=title)
    except AudioImportError as error:
        console.print(f"[red]No se pudo importar:[/red] {error}")
        raise typer.Exit(1) from error
    console.print(f"[green]Audio importado localmente[/green] — sesión {session.id}")
    console.print(f"Audio: {session.audio_path}")
    console.print(f"Transcribe con: hayvoz transcribe {session.id}")


@model_app.command("download")
def download_model_command(
    model: Annotated[
        WhisperModelName,
        typer.Option(
            "--model", case_sensitive=False, help="tiny, base, small o medium."
        ),
    ] = WhisperModelName.SMALL,
) -> None:
    """Descarga explícitamente un modelo; nunca acepta large."""
    runtime = _runtime()
    manager = WhisperModelManager(runtime.settings)
    console.print(
        f"Descargando Whisper {model.value} desde Hugging Face. "
        "No se envía audio ni transcripción."
    )
    try:
        with console.status(f"Descargando modelo {model.value}..."):
            path, downloaded = manager.download(model)
    except ModelManagerError as error:
        console.print(f"[red]No se pudo descargar:[/red] {error}")
        raise typer.Exit(1) from error
    action = "descargado" if downloaded else "ya estaba instalado"
    console.print(f"[green]Modelo {action}[/green]: {path}")


@app.command()
def transcribe(
    session_id: Annotated[str, typer.Argument(help="ID completo de la sesión.")],
    model: Annotated[
        WhisperModelName | None,
        typer.Option("--model", case_sensitive=False, help="Modelo local a utilizar."),
    ] = None,
    language: Annotated[
        str | None,
        typer.Option("--language", help="Código ISO, por ejemplo es o en."),
    ] = None,
    speaker: Annotated[
        Speaker,
        typer.Option("--speaker", case_sensitive=False, help="Etiqueta del canal."),
    ] = Speaker.INTERVIEWER,
) -> None:
    """Transcribe offline una sesión; combina sus dos fuentes si existen."""
    runtime = _runtime()
    try:
        selected_model = model or WhisperModelName(runtime.settings.whisper_model)
    except ValueError as error:
        console.print("[red]WHISPER_MODEL debe ser tiny, base, small o medium.[/red]")
        raise typer.Exit(1) from error
    service = _transcription_service(runtime, selected_model)
    selected_language = language or runtime.settings.whisper_language
    try:
        with console.status(
            f"Transcribiendo localmente con {selected_model.value} (CPU int8)..."
        ):
            result = service.transcribe(
                session_id,
                language=selected_language,
                speaker=speaker,
            )
    except TranscriptionServiceError as error:
        console.print(f"[red]No se pudo transcribir:[/red] {error}")
        raise typer.Exit(1) from error
    language_detail = result.language or "no detectado"
    if result.language_probability is not None:
        language_detail += f" ({result.language_probability:.1%})"
    console.print(
        f"[green]Transcripción completada[/green] — {result.segment_count} segmentos\n"
        f"Idioma: {language_detail}\n"
        f"JSON: {result.transcript_path}"
    )


@app.command()
def transcript(
    session_id: Annotated[str, typer.Argument(help="ID completo de la sesión.")],
) -> None:
    """Muestra la transcripción persistida sin acceso de red."""
    runtime = _runtime()
    try:
        selected_model = WhisperModelName(runtime.settings.whisper_model)
    except ValueError:
        selected_model = WhisperModelName.SMALL
    service = _transcription_service(runtime, selected_model)
    try:
        segments = service.get_segments(session_id)
    except TranscriptionServiceError as error:
        console.print(f"[red]No se pudo leer:[/red] {error}")
        raise typer.Exit(1) from error
    if not segments:
        console.print(
            f"No hay segmentos. Ejecuta primero: hayvoz transcribe {session_id}"
        )
        return
    for segment in segments:
        console.print(
            f"[dim]{_timestamp(segment.start)} → {_timestamp(segment.end)}[/dim] "
            f"[bold]{segment.speaker.value}:[/bold] {segment.text}"
        )
    console.print(
        f"\nJSON: {TranscriptJsonStore(runtime.settings).path_for(session_id)}"
    )


@app.command()
def assistant(
    session_id: Annotated[str, typer.Argument(help="ID de una sesión Assistant.")],
    watch: Annotated[
        bool,
        typer.Option("--watch", help="Actualiza la vista hasta que presiones Ctrl-C."),
    ] = False,
    refresh_seconds: Annotated[
        float,
        typer.Option("--refresh-seconds", min=0.5, max=60),
    ] = 3.0,
) -> None:
    """Muestra transcripción incremental y la última sugerencia persistida."""
    runtime = _runtime()
    localized_assistant = assistant_term(runtime.settings.language)
    service = AssistantService(
        runtime.sessions,
        TranscriptRepository(runtime.database),
        AssistantRepository(runtime.database),
        TranscriptJsonStore(runtime.settings),
        InterviewGuideStore(runtime.settings),
        FasterWhisperTranscriber(runtime.settings, _configured_whisper_model(runtime)),
        None,
        language=runtime.settings.whisper_language,
    )
    try:
        while True:
            runtime.session_service.recover_orphans()
            snapshot = service.snapshot(session_id)
            if watch:
                console.clear()
            _render_assistant_snapshot(snapshot, localized_assistant)
            if not watch or snapshot.session.status.value not in {
                "starting",
                "recording",
                "stopping",
            }:
                return
            time.sleep(refresh_seconds)
    except AssistantServiceError as error:
        console.print(f"[red]No se pudo leer {localized_assistant}:[/red] {error}")
        raise typer.Exit(1) from error
    except KeyboardInterrupt:
        console.print(f"\nVista {localized_assistant} cerrada; la grabación continúa.")


for _assistant_alias in assistant_aliases():
    if _assistant_alias != "assistant":
        app.command(_assistant_alias, hidden=True)(assistant)


def _parse_session_mode(value: str) -> SessionMode:
    normalized = value.strip().casefold()
    if normalized == SessionMode.RECORD.value:
        return SessionMode.RECORD
    if normalized in assistant_aliases():
        return SessionMode.ASSISTANT
    accepted = ", ".join((SessionMode.RECORD.value, *assistant_aliases()))
    raise typer.BadParameter(f"Modo inválido. Usa uno de: {accepted}.")


def _configured_whisper_model(runtime: Runtime) -> WhisperModelName:
    try:
        return WhisperModelName(runtime.settings.whisper_model)
    except ValueError:
        return WhisperModelName.SMALL


def _render_assistant_snapshot(
    snapshot: AssistantSnapshot, localized_assistant: str = "Assistant"
) -> None:
    console.print(
        f"[bold]{snapshot.session.title}[/bold] · "
        f"estado: {snapshot.session.status.value}"
    )
    if snapshot.recent_segments:
        transcript_lines = [
            f"[{_timestamp(segment.start)}] {segment.speaker.value}: {segment.text}"
            for segment in snapshot.recent_segments
        ]
        console.print(
            Panel("\n".join(transcript_lines), title="Transcripción reciente")
        )
    else:
        console.print("[dim]Aún no hay segmentos transcritos.[/dim]")

    update = snapshot.latest_update
    if update is None:
        detail = (
            "La sesión es local-only; no se generan sugerencias externas."
            if snapshot.session.local_only
            else "Aún no hay una sugerencia persistida."
        )
        console.print(f"[dim]{detail}[/dim]")
        return
    console.print(Panel(update.suggested_question, title="Siguiente pregunta sugerida"))
    console.print(f"[bold]Motivo:[/bold] {update.rationale}")
    console.print(f"[bold]Resumen acumulado:[/bold] {update.rolling_summary}")
    asked = "\n".join(f"- {item}" for item in update.asked_questions) or "- Ninguna"
    pending = "\n".join(f"- {item}" for item in update.pending_questions) or "- Ninguna"
    console.print(
        Markdown(f"### Preguntas realizadas\n{asked}\n\n### Pendientes\n{pending}")
    )
    console.print(f"[dim]Modelo: {update.model} · {update.created_at}[/dim]")


@app.command()
def analyze(
    session_id: Annotated[str, typer.Argument(help="ID completo de la sesión.")],
    confirm_send: Annotated[
        bool,
        typer.Option(
            "--confirm-send",
            help="Confirma el envío del título y la transcripción al proveedor de IA.",
        ),
    ] = False,
) -> None:
    """Revisa o envía texto al proveedor configurado para generar análisis."""
    runtime = _runtime()
    service = _analysis_service(runtime)
    try:
        preview = service.preview(session_id)
    except AnalysisServiceError as error:
        console.print(f"[red]No se pudo analizar:[/red] {error}")
        raise typer.Exit(1) from error

    console.print(
        f"Contenido externo: título y {preview.segment_count} segmento(s) "
        f"({preview.character_count} caracteres de conversación)."
    )
    console.print("El audio no se envía.")

    if not confirm_send:
        transcript_lines = [
            f"[{_timestamp(turn.start)} → {_timestamp(turn.end)}] "
            f"{turn.speaker}: {turn.text}"
            for turn in preview.request.turns
        ]
        console.print(
            Panel(
                "\n".join(transcript_lines),
                title=f"Vista previa — {preview.request.title}",
            )
        )
        if preview.local_only:
            console.print(
                "[yellow]No se envió nada.[/yellow] La sesión es local-only y "
                "no admite llamadas externas."
            )
        else:
            console.print(
                "[yellow]No se envió nada.[/yellow] Revisa el texto y repite con "
                f"--confirm-send: hayvoz analyze {session_id} --confirm-send"
            )
        return

    if preview.local_only:
        console.print(
            "[red]No se pudo analizar:[/red] La sesión fue creada con --local-only "
            "y no puede enviarse al proveedor de IA."
        )
        raise typer.Exit(1)

    try:
        provider = create_provider(runtime.settings)
        service = _analysis_service(runtime, provider)
        with console.status(f"Analizando texto con {provider.provider_name}..."):
            analyses = service.analyze(session_id, allow_external=True)
    except (AnalysisServiceError, LLMProviderError) as error:
        console.print(f"[red]No se pudo analizar:[/red] {error}")
        raise typer.Exit(1) from error
    console.print(
        f"[green]Análisis completado[/green] — {len(analyses)} resultados "
        f"persistidos con {provider.model}."
    )
    console.print(f"Consulta el informe con: hayvoz report {session_id}")


@app.command()
def report(
    session_id: Annotated[str, typer.Argument(help="ID completo de la sesión.")],
) -> None:
    """Muestra el informe persistido sin llamadas de red."""
    runtime = _runtime()
    try:
        runtime.sessions.get(session_id)
    except SessionNotFoundError as error:
        console.print(f"[red]No existe la sesión {session_id}.[/red]")
        raise typer.Exit(1) from error
    analysis = AnalysisRepository(runtime.database).get_for_type(
        session_id,
        AnalysisType.FINAL_REPORT,
    )
    if analysis is None:
        console.print(
            "No hay informe persistido. Revisa primero el envío con: "
            f"hayvoz analyze {session_id}"
        )
        return
    console.print(Markdown(analysis.content))
    console.print(
        f"\n[dim]Modelo: {analysis.model} · generado: {analysis.created_at}[/dim]"
    )


def _timestamp(seconds: float) -> str:
    minutes, remaining = divmod(seconds, 60)
    return f"{int(minutes):02d}:{remaining:05.2f}"


if __name__ == "__main__":
    app()
