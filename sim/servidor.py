"""API HTTP local para disparar eventos no simulador.

    POST /evento   {"evento": "erro", "detalhe": "3 testes falharam", "pet": "auto"}
    GET  /         status (pets carregados, tamanho da fila)
"""

from __future__ import annotations

import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def iniciar(fila: "queue.Queue[dict]", pets: list[str], porta: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def _responder(self, codigo: int, corpo: dict) -> None:
            dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def do_GET(self) -> None:  # noqa: N802
            self._responder(200, {"pets": pets, "fila": fila.qsize()})

        def do_POST(self) -> None:  # noqa: N802
            if self.path.rstrip("/") != "/evento":
                return self._responder(404, {"erro": "use POST /evento"})
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
                evento = json.loads(self.rfile.read(tamanho) or b"{}")
                if not isinstance(evento, dict) or "evento" not in evento:
                    raise ValueError('campo "evento" é obrigatório')
            except (ValueError, json.JSONDecodeError) as e:
                return self._responder(400, {"erro": str(e)})
            fila.put(evento)
            self._responder(202, {"ok": True})

        def log_message(self, *args) -> None:
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", porta), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor
