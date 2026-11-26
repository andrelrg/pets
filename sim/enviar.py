"""Envia um evento para o simulador em execução.

Uso:
    python -m sim.enviar erro "3 testes falharam"
    python -m sim.enviar sucesso "build ok" --pet nala
    python -m sim.enviar progresso "migração" --valor 60 --silencioso   # só atualiza a barra
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def enviar(evento: str, detalhe: str = "", pet: str = "auto", prioridade: str = "normal",
           porta: int = 8765, valor: float | None = None, silencioso: bool = False) -> dict:
    dados = {"evento": evento, "detalhe": detalhe, "pet": pet, "prioridade": prioridade}
    if valor is not None:
        dados["valor"] = valor
    if silencioso:
        dados["silencioso"] = True
    corpo = json.dumps(dados).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{porta}/evento", data=corpo,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=3) as r:
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser(prog="sim.enviar", description="Envia um evento ao simulador.")
    ap.add_argument("evento", help="erro | aviso | sucesso | progresso | pendente | marco | deploy | info")
    ap.add_argument("detalhe", nargs="?", default="")
    ap.add_argument("--pet", default="auto", help="id do pet, auto ou ambos")
    ap.add_argument("--prioridade", default="normal", choices=["baixa", "normal", "alta"])
    ap.add_argument("--valor", type=float, help="progresso 0-100 (barra no painel)")
    ap.add_argument("--silencioso", action="store_true", help="só atualiza o painel, sem fala")
    ap.add_argument("--porta", type=int, default=8765)
    a = ap.parse_args()
    try:
        enviar(a.evento, a.detalhe, a.pet, a.prioridade, a.porta, a.valor, a.silencioso)
    except urllib.error.URLError:
        sys.exit("Simulador não está rodando (python -m sim).")


if __name__ == "__main__":
    main()
