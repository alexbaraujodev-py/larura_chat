from __future__ import annotations

import shutil
import signal
import subprocess
import threading
from pathlib import Path
from typing import Protocol


class SpeechEngine(Protocol):
    def say(self, text: str) -> None: ...

    def runAndWait(self) -> None: ...


class AudioError(RuntimeError):
    """Raised when local audio support is unavailable."""


class Recorder:
    def __init__(self, output: Path) -> None:
        self.output = output
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def recording(self) -> bool:
        return self._process is not None

    def start(self) -> None:
        if self.recording:
            raise AudioError("A gravação já está em andamento.")
        if shutil.which("arecord") is None:
            raise AudioError("O comando 'arecord' não foi encontrado.")
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self._process = subprocess.Popen(
            [
                "arecord",
                "--quiet",
                "--format",
                "S16_LE",
                "--rate",
                "16000",
                "--channels",
                "1",
                "--file-type",
                "wav",
                str(self.output),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    def stop(self) -> Path:
        if self._process is None:
            raise AudioError("Não há gravação em andamento.")
        process = self._process
        self._process = None
        process.send_signal(signal.SIGINT)
        _, stderr = process.communicate()
        valid_recording = self.output.exists() and self.output.stat().st_size > 44
        if process.returncode not in (0, -signal.SIGINT) and not valid_recording:
            detail = stderr.decode(errors="replace").strip()
            raise AudioError(detail or "Não foi possível gravar pelo microfone.")
        if not valid_recording:
            raise AudioError("A gravação não produziu um arquivo de áudio.")
        return self.output


class Transcriber:
    def __init__(self, model_name: str, language: str) -> None:
        self.model_name = model_name
        self.language = language
        self._model = None

    def transcribe(self, audio_path: Path) -> str:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise AudioError(
                "Transcrição local indisponível. Instale as dependências com "
                "'uv sync'."
            ) from exc

        if self._model is None:
            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
            )
        try:
            segments, _ = self._model.transcribe(
                str(audio_path),
                language=self.language,
                vad_filter=True,
            )
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise AudioError(f"Falha ao transcrever o áudio: {exc}") from exc
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise AudioError("Não foi possível entender o áudio.")
        return text


class Speaker:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._engine: SpeechEngine | None = None

    def say(self, text: str) -> None:
        if not self.enabled or not text:
            return
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            engine = self._engine
            engine.say(text)
            threading.Thread(target=self._run_engine, args=(engine,), daemon=True).start()
        except (ImportError, RuntimeError):
            # Text output remains available when no local speech engine exists.
            return

    def _run_engine(self, engine: SpeechEngine) -> None:
        try:
            engine.runAndWait()
        except RuntimeError:
            return
