from __future__ import annotations

import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

from .audio import AudioError, Recorder, Speaker, Transcriber
from .config import Settings
from .hermes import HermesClient, HermesError


class FalarApp:
    def __init__(self, root: tk.Tk, settings: Settings) -> None:
        self.root = root
        self.settings = settings
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.recorder = Recorder(
            settings.recordings_dir
            / f"recording-{datetime.now():%Y%m%d-%H%M%S}.wav"
        )
        self.transcriber = Transcriber(settings.whisper_model, settings.language)
        self.speaker = Speaker()
        self.hermes = HermesClient(settings.hermes_command, settings.workdir)
        self._build_ui()
        self.root.after(100, self._drain_events)

    def _build_ui(self) -> None:
        self.root.title("Falar — Hermes Agent")
        self.root.geometry("760x520")
        self.root.minsize(620, 400)

        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Falar", font=("TkDefaultFont", 20, "bold")).pack(
            anchor=tk.W
        )
        ttk.Label(
            frame,
            text="Fale uma tarefa e acompanhe o Hermes executando-a.",
        ).pack(anchor=tk.W, pady=(0, 12))

        self.log = tk.Text(frame, state=tk.DISABLED, wrap=tk.WORD, height=18)
        self.log.pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(frame)
        controls.pack(fill=tk.X, pady=(12, 0))
        self.record_button = ttk.Button(
            controls, text="● Começar gravação", command=self._toggle_recording
        )
        self.record_button.pack(side=tk.LEFT)
        self.status = ttk.Label(controls, text="Pronto")
        self.status.pack(side=tk.LEFT, padx=12)

    def _toggle_recording(self) -> None:
        try:
            if self.recorder.recording:
                audio_path = self.recorder.stop()
                self.record_button.configure(text="● Começar gravação")
                self._set_status("Transcrevendo...")
                self._run_background(self._transcribe_and_run, audio_path)
            else:
                self.recorder.start()
                self.record_button.configure(text="■ Parar e executar")
                self._set_status("Escutando...")
                self._write("Você pode falar agora.")
                self.speaker.say("Pode falar agora.")
        except AudioError as exc:
            self._show_error(str(exc))

    def _transcribe_and_run(self, audio_path: Path) -> None:
        try:
            prompt = self.transcriber.transcribe(audio_path)
            self.events.put(("transcript", prompt))
            self.events.put(("status", "Hermes está trabalhando..."))
            self.speaker.say("Entendi. Hermes está trabalhando.")
            self.hermes.run(prompt, lambda line: self.events.put(("output", line)))
            self.events.put(("status", "Concluído"))
            self.speaker.say("Tarefa concluída.")
        except (AudioError, HermesError) as exc:
            self.events.put(("error", str(exc)))

    def _run_background(
        self, target: Callable[[Path], None], argument: Path
    ) -> None:
        threading.Thread(target=target, args=(argument,), daemon=True).start()

    def _drain_events(self) -> None:
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "transcript":
                self._write(f"Você: {value}")
            elif kind == "output":
                self._write(f"Hermes: {value}")
            elif kind == "status":
                self._set_status(value)
            elif kind == "error":
                self._show_error(value)
        self.root.after(100, self._drain_events)

    def _write(self, text: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def _show_error(self, message: str) -> None:
        self._set_status("Erro")
        self._write(f"Erro: {message}")
        messagebox.showerror("Falar", message)


def main() -> None:
    root = tk.Tk()
    FalarApp(root, Settings())
    root.mainloop()


if __name__ == "__main__":
    main()
