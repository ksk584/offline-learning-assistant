"""Command line interface for the Offline Intelligent Lecture Assistant."""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from ila import __version__
from ila.asr import create_asr
from ila.audio import FileSource, MicrophoneSource, list_input_devices
from ila.config import Settings, ila_home, load_settings
from ila.events import CaptionEvent, SessionSummary
from ila.pipeline import CaptionPipeline
from ila.segmenter import SpeechSegmenter

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)
console = Console()

ModelOpt = Annotated[
    str | None, typer.Option("--model", "-m", help="Whisper model, e.g. base.en, small.en")
]
LanguageOpt = Annotated[
    str | None,
    typer.Option("--language", "-l", help="Language code, or 'auto' to detect"),
]
NoPartialsOpt = Annotated[bool, typer.Option("--no-partials", help="Only emit finalized captions")]


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _build_settings(
    model: str | None,
    language: str | None,
    *,
    partials: bool = True,
) -> Settings:
    settings = load_settings()
    if model:
        settings.asr.model = model
    if language is not None:
        settings.asr.language = None if language.lower() == "auto" else language
    if not partials:
        settings.partials.enabled = False
    return settings


def _fmt_time(seconds: float) -> str:
    minutes, rest = divmod(max(0.0, seconds), 60)
    return f"{int(minutes):02d}:{rest:04.1f}"


class CaptionPrinter:
    """Renders finals as transcript lines and the in-progress partial beneath."""

    def __init__(self, *, max_lines: int = 14) -> None:
        self._finals: deque[Text] = deque(maxlen=max_lines)
        self._partial = ""
        self._terminal = console.is_terminal
        self._live: Live | None = (
            Live(console=console, refresh_per_second=10, vertical_overflow="visible")
            if self._terminal
            else None
        )

    def start(self) -> None:
        if self._live is not None:
            self._live.start()

    def handle(self, event: CaptionEvent) -> None:
        if event.final:
            stamp = Text(f"{_fmt_time(event.start)} ", style="dim")
            line = Text.assemble(stamp, event.text)
            self._finals.append(line)
            self._partial = ""
            if self._live is None:
                console.print(line)
        else:
            self._partial = event.text
        if self._live is not None:
            self._live.update(self._render(), refresh=True)

    def _render(self) -> Text:
        body = Text()
        for line in self._finals:
            body.append_text(line)
            body.append("\n")
        if self._partial:
            body.append("> ", style="bold cyan")
            body.append(self._partial, style="italic")
        else:
            body.append("\u2588", style="dim")
        return body

    def stop(self) -> None:
        if self._live is not None:
            self._live.stop()
            for line in self._finals:
                console.print(line)


def _run(settings: Settings, source, *, stop=None) -> SessionSummary:
    """Shared driver for live capture and file transcription."""
    asr = create_asr(settings.asr)
    pipeline = CaptionPipeline.from_settings(settings, source, asr)
    printer = CaptionPrinter()
    summary = SessionSummary()
    started = time.perf_counter()

    console.print(
        f"[bold]{asr.info.engine}[/bold] model=[cyan]{asr.info.model}[/cyan] "
        f"device={asr.info.device} compute={asr.info.compute_type}"
    )
    printer.start()
    try:
        for event in pipeline.events(stop=stop):
            summary.events.append(event)
            if event.final:
                summary.utterances += 1
                summary.audio_s = max(summary.audio_s, event.end)
            printer.handle(event)
    except KeyboardInterrupt:
        console.print("\n[dim]stopped[/dim]")
    finally:
        printer.stop()
        summary.wall_s = time.perf_counter() - started
        source.close()
    return summary


@app.command()
def live(
    model: ModelOpt = None,
    language: LanguageOpt = None,
    device: Annotated[
        int | None, typer.Option("--device", "-d", help="Microphone device index")
    ] = None,
    no_partials: NoPartialsOpt = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Caption a live microphone feed in the terminal (Ctrl+C to stop)."""
    _configure_logging(verbose)
    settings = _build_settings(model, language, partials=not no_partials)
    if device is not None:
        settings.audio.device = device
    source = MicrophoneSource(
        sample_rate=settings.audio.sample_rate,
        block_ms=settings.audio.block_ms,
        device=settings.audio.device,
    )
    console.print(f"[dim]listening...[/dim] model={settings.asr.model}")
    summary = _run(settings, source)
    _print_summary(summary, settings)


@app.command()
def transcribe(
    path: Annotated[Path, typer.Argument(help="Audio/video file to transcribe")],
    model: ModelOpt = None,
    language: LanguageOpt = None,
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="Write caption events as JSONL")
    ] = None,
    text_out: Annotated[
        Path | None, typer.Option("--text-out", help="Write the plain transcript to a file")
    ] = None,
    realtime: Annotated[
        bool, typer.Option("--realtime", help="Pace playback at real time")
    ] = False,
    no_partials: NoPartialsOpt = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Transcribe an audio/video file entirely on-device."""
    _configure_logging(verbose)
    if not path.exists():
        raise typer.BadParameter(f"File not found: {path}")
    settings = _build_settings(model, language, partials=not no_partials)
    source = FileSource(
        path,
        sample_rate=settings.audio.sample_rate,
        block_ms=settings.audio.block_ms,
        realtime=realtime,
    )
    console.print(f"[dim]file[/dim] {path} [dim]({source.duration_s:.1f}s)[/dim]")
    summary = _run(settings, source)

    if out:
        _write_jsonl(out, summary.events)
        console.print(f"[green]events[/green] {out}")
    if text_out:
        text_out.parent.mkdir(parents=True, exist_ok=True)
        text_out.write_text(summary.transcript + "\n", encoding="utf-8")
        console.print(f"[green]transcript[/green] {text_out}")
    _print_summary(summary, settings)


def _print_summary(summary: SessionSummary, settings: Settings) -> None:
    console.print(
        f"[dim]utterances[/dim] {summary.utterances} "
        f"[dim]transcribed[/dim] {summary.audio_s:.1f}s audio "
        f"[dim]in[/dim] {summary.wall_s:.1f}s "
        f"([cyan]{summary.realtime_factor:.1f}x[/cyan] realtime) "
        f"[dim]model[/dim] {settings.asr.model}"
    )
    console.print(summary.transcript, markup=False)


def _write_jsonl(path: Path, events: list[CaptionEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")


@app.command()
def serve(
    host: Annotated[str | None, typer.Option(help="Bind address")] = None,
    port: Annotated[int | None, typer.Option(help="Port")] = None,
    reload: Annotated[bool, typer.Option("--reload", help="Auto-reload on code changes")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Run the local WebSocket API (for the dashboard and integrations)."""
    import uvicorn

    _configure_logging(verbose)
    settings = load_settings()
    uvicorn.run(
        "ila.server:app",
        host=host or settings.server.host,
        port=port or settings.server.port,
        reload=reload,
        log_level="debug" if verbose else "info",
    )


@app.command()
def devices() -> None:
    """List available microphone input devices."""
    try:
        found = list_input_devices()
    except Exception as exc:
        console.print(f"[red]Could not query audio devices:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    if not found:
        console.print("[yellow]No input devices found.[/yellow]")
        return
    table = Table(title="Input devices", show_lines=False)
    table.add_column("Index", justify="right")
    table.add_column("Name")
    table.add_column("Channels", justify="right")
    table.add_column("Host API")
    table.add_column("Default")
    for item in found:
        table.add_row(
            str(item["index"]),
            str(item["name"]),
            str(item["channels"]),
            str(item["host_api"]),
            "yes" if item["default"] else "",
        )
    console.print(table)


@app.command("download-model")
def download_model(
    name: Annotated[str | None, typer.Argument(help="Whisper model to download")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Download a Whisper model for offline use (one-time network access)."""
    _configure_logging(verbose)
    settings = load_settings()
    if name:
        settings.asr.model = name
    settings.asr.local_files_only = False
    console.print(f"[dim]fetching[/dim] {settings.asr.model} -> {settings.asr.model_dir}")
    info = create_asr(settings.asr).info
    console.print(f"[green]ready[/green] {info.model} on {info.device} ({info.compute_type})")
    console.print("[dim]Set ILA_ASR__LOCAL_FILES_ONLY=true to guarantee offline use.[/dim]")


@app.command()
def info() -> None:
    """Show resolved configuration and environment details."""
    import platform

    settings = load_settings()
    console.print(f"[bold]ila[/bold] {__version__}  python {platform.python_version()}")
    console.print(f"[dim]home[/dim] {ila_home()}")
    console.print(settings.model_dump_json(indent=2))


@app.command()
def calibrate(
    seconds: Annotated[float, typer.Option(help="Seconds of room tone to sample")] = 3.0,
    device: Annotated[int | None, typer.Option("--device", "-d")] = None,
) -> None:
    """Measure the room's noise floor to sanity-check VAD thresholds."""
    source = MicrophoneSource(device=device)
    segmenter = SpeechSegmenter(sample_rate=source.sample_rate)
    console.print(f"[dim]sampling {seconds:.0f}s of room tone - stay quiet[/dim]")
    deadline = time.monotonic() + seconds
    levels: list[float] = []
    frame_samples = segmenter.frame_samples
    try:
        for block in source.blocks():
            for start in range(0, block.size - frame_samples + 1, frame_samples):
                frame = block[start : start + frame_samples]
                segmenter.feed(frame)
            levels.append(segmenter.noise_floor_db)
            if time.monotonic() >= deadline:
                break
    except KeyboardInterrupt:
        pass
    finally:
        source.close()
    if not levels:
        console.print("[red]No audio captured.[/red]")
        raise typer.Exit(code=1)
    floor = levels[-1]
    console.print(
        f"[green]noise floor[/green] {floor:.1f} dBFS  "
        f"[dim]speech gate[/dim] {floor + 8.0:.1f} dBFS"
    )
    console.print(
        "[dim]If the gate is below your normal speaking level by 8-15 dB, "
        "defaults are fine. Otherwise set ILA_VAD__START_MARGIN_DB.[/dim]"
    )


if __name__ == "__main__":  # pragma: no cover
    app()
