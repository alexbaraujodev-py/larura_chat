from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    hermes_command: str = os.getenv("HERMES_COMMAND", "hermes")
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    language: str = os.getenv("SPEECH_LANGUAGE", "pt")
    workdir: Path = Path(os.getenv("HERMES_WORKDIR", Path.cwd()))
    recordings_dir: Path = Path(
        os.getenv("RECORDINGS_DIR", Path.home() / ".local" / "share" / "falar")
    )

