from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable


class HermesError(RuntimeError):
    """Raised when Hermes cannot be started or returns an error."""


class HermesClient:
    def __init__(self, command: str, workdir: Path) -> None:
        self.command = command
        self.workdir = workdir

    def run(
        self,
        prompt: str,
        on_output: Callable[[str], None],
    ) -> int:
        try:
            process = subprocess.Popen(
                [
                    self.command,
                    "-z",
                    prompt,
                    "--cli",
                    "--no-restore-cwd",
                ],
                cwd=self.workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise HermesError(
                f"Não foi possível iniciar '{self.command}': {exc}"
            ) from exc

        assert process.stdout is not None
        output_lines: list[str] = []
        for line in process.stdout:
            cleaned = line.rstrip()
            if cleaned:
                output_lines.append(cleaned)
                on_output(cleaned)
        return_code = process.wait()
        if return_code != 0:
            detail = "\n".join(output_lines[-5:])
            message = f"Hermes terminou com código {return_code}."
            if detail:
                message += f"\n\nDetalhes:\n{detail}"
            raise HermesError(message)
        return return_code
