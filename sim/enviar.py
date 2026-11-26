"""Envia um evento para o simulador em execução ou para o aparelho (firmware).

Uso:
    python -m sim.enviar erro "3 testes falharam"
    python -m sim.enviar sucesso "build ok" --pet nala
    python -m sim.enviar progresso "migração" --valor 60 --silencioso   # só atualiza a barra
    python -m sim.enviar progresso "migração" --valor 100                # concluída (comemora)
    python -m sim.enviar sucesso "migração"                              # também conclui
    python -m sim.enviar progresso "build" --limite 300                  # alerta se parar 5 min
    python -m sim.enviar deploy "v1.4" --host pets.local                 # no aparelho

O destino padrão pode vir da variável de ambiente PETS_HOST.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def enviar(evento: str, detalhe: str = "", pet: str = "auto", prioridade: str = "normal",
           porta: int = 8765, valor: float | None = None, silencioso: bool = False,
           host: str | None = None, limite: float | None = None) -> dict:
    dados = {"evento": evento, "detalhe": detalhe, "pet": pet, "prioridade": prioridade}
    if valor is not None:
        dados["valor"] = valor
    if silencioso:
        dados["silencioso"] = True
    if limite is not None:
        dados["limite"] = limite
    corpo = json.dumps(dados).encode("utf-8")
    req = urllib.request.Request(
        f"http://{host or os.environ.get('PETS_HOST', '127.0.0.1')}:{porta}/evento", data=corpo,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser(prog="sim.enviar", description="Envia um evento ao simulador ou ao aparelho.")
    ap.add_argument("evento", help="erro | aviso | sucesso | progresso | pendente | marco | deploy | info")
    ap.add_argument("detalhe", nargs="?", default="")
    ap.add_argument("--pet", default="auto", help="id do pet, auto ou ambos")
    ap.add_argument("--prioridade", default="normal", choices=["baixa", "normal", "alta"])
    ap.add_argument("--valor", type=float, help="progresso 0-100 (barra no painel)")
    ap.add_argument("--silencioso", action="store_true", help="só atualiza o painel, sem fala")
    ap.add_argument("--limite", type=float,
                    help="progresso: segundos sem novo progresso até o alerta de tarefa parada")
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument("--host", help="destino (padrão: $PETS_HOST ou 127.0.0.1); ex.: pets.local")
    a = ap.parse_args()
    try:
        enviar(a.evento, a.detalhe, a.pet, a.prioridade, a.porta, a.valor, a.silencioso, a.host, a.limite)
    except urllib.error.URLError:
        destino = a.host or os.environ.get("PETS_HOST")
        sys.exit(f"Sem resposta de {destino}." if destino else "Simulador não está rodando (python -m sim).")


if __name__ == "__main__":
    main()
