from __future__ import annotations

import hmac
import json
import secrets
import threading
import uuid
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import Settings
from .hermes import HermesClient, HermesError


@dataclass
class RunState:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: str = "Pronto para ouvir"
    phase: str = "idle"
    transcript: str = ""
    output: list[str] = field(default_factory=list)
    error: str | None = None
    running: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "phase": self.phase,
            "transcript": self.transcript,
            "output": self.output[-500:],
            "error": self.error,
            "running": self.running,
        }


class WebApplication:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.hermes = HermesClient(settings.hermes_command, settings.workdir)
        self.state = RunState()
        self.csrf_token = secrets.token_urlsafe(32)
        self._lock = threading.Lock()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self.state.as_dict()

    def start_run(self, prompt: str) -> None:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Diga o que você precisa que seja feito.")
        with self._lock:
            if self.state.running:
                raise RuntimeError("Já existe uma tarefa em andamento.")
            self.state = RunState(
                status="Hermes está trabalhando...",
                phase="running",
                transcript=prompt,
                running=True,
            )
        threading.Thread(target=self._run, args=(prompt,), daemon=True).start()

    def _run(self, prompt: str) -> None:
        try:
            self.hermes.run(prompt, self._append_output)
        except HermesError as exc:
            with self._lock:
                self.state.status = "Não foi possível concluir"
                self.state.phase = "error"
                self.state.error = str(exc)
                self.state.running = False
            return
        with self._lock:
            self.state.status = "Tarefa concluída"
            self.state.phase = "completed"
            self.state.running = False

    def _append_output(self, line: str) -> None:
        with self._lock:
            self.state.output.append(line)


class RequestHandler(BaseHTTPRequestHandler):
    application: WebApplication
    static_dir = Path(__file__).with_name("web")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/status":
            self._json(HTTPStatus.OK, self.application.snapshot())
            return
        if path in {"/", "/index.html"}:
            self._file("index.html", "text/html; charset=utf-8")
            return
        if path in {
            "/styles.css",
            "/app.js",
            "/olhos_front.png",
            "/bailarina_novo_teste.gif",
        }:
            content_type = "text/css; charset=utf-8" if path.endswith(".css") else "text/javascript; charset=utf-8"
            if path.endswith(".png"):
                content_type = "image/png"
            if path.endswith(".gif"):
                content_type = "image/gif"
            self._file(path.removeprefix("/"), content_type)
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "Recurso não encontrado."})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/run":
            self._json(HTTPStatus.NOT_FOUND, {"error": "Rota não encontrada."})
            return
        origin = self.headers.get("Origin", "")
        if origin not in {"http://127.0.0.1:8765", "http://localhost:8765"}:
            self._json(HTTPStatus.FORBIDDEN, {"error": "Origem não autorizada."})
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Content-Type deve ser application/json."})
            return
        provided_token = self.headers.get("X-Falar-Token", "")
        if not hmac.compare_digest(provided_token, self.application.csrf_token):
            self._json(HTTPStatus.FORBIDDEN, {"error": "Token de autorização inválido."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("Corpo da requisição vazio.")
            payload = json.loads(self.rfile.read(length))
            self.application.start_run(str(payload.get("prompt", "")))
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except RuntimeError as exc:
            self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
            return
        self._json(HTTPStatus.ACCEPTED, self.application.snapshot())

    def _file(self, name: str, content_type: str) -> None:
        try:
            content = (self.static_dir / name).read_bytes()
        except OSError:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Arquivo da interface não encontrado."})
            return
        if name == "index.html":
            content = content.replace(
                b'<meta name="viewport" content="width=device-width, initial-scale=1">',
                (
                    b'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                    + f'<meta name="falar-token" content="{self.application.csrf_token}">'.encode("ascii")
                ),
            )
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        if name == "index.html":
            self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    settings = Settings()
    application = WebApplication(settings)
    handler = type("FalarRequestHandler", (RequestHandler,), {"application": application})
    server = ThreadingHTTPServer(("127.0.0.1", 8765), handler)
    print("Falar web disponível em http://127.0.0.1:8765")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
