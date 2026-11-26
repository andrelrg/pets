"""Simulador dos pets no PC.

Uso (na raiz do repositório):
    python -m sim                      # janela 240x240 ampliada 3x
    python -m sim --escala 2 --porta 8765
    python -m sim --demo               # dispara eventos de exemplo sozinho

Enquanto roda, aceita eventos por HTTP (ver sim/enviar.py):
    python -m sim.enviar erro "3 testes falharam"

    python -m sim --dormir 5 --carinho 3 6   # ver logo a cena de carinho

Teclas: 1 erro · 2 aviso · 3 sucesso · 4 progresso · 5 pendente · 6 marco ·
        7 deploy · 0 os dois falam · S salva captura em build/sim.png · Esc sai
"""

from __future__ import annotations

import argparse
import random

import pygame

from . import servidor
from .app import Simulador
from .recursos import RAIZ, carregar_pets

EXEMPLOS = [
    {"evento": "erro", "detalhe": "3 testes falharam no módulo de pagamentos"},
    {"evento": "aviso", "detalhe": "o disco está com 90% de uso"},
    {"evento": "sucesso", "detalhe": "build concluído em 42s"},
    {"evento": "progresso", "detalhe": "migração 60% concluída"},
    {"evento": "pendente", "detalhe": "revisar o PR #12"},
    {"evento": "marco", "detalhe": "versão 1.0 publicada"},
    {"evento": "deploy", "detalhe": "produção"},
]
TECLAS = {getattr(pygame, f"K_{i + 1}"): ev for i, ev in enumerate(EXEMPLOS)}


def main() -> None:
    ap = argparse.ArgumentParser(prog="sim", description="Simulador dos pets.")
    ap.add_argument("--pets", nargs="*", help="ids dos pets (padrão: todos)")
    ap.add_argument("--largura", type=int, default=240)
    ap.add_argument("--altura", type=int, default=240)
    ap.add_argument("--escala", type=int, default=3)
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument("--demo", action="store_true", help="dispara eventos de exemplo")
    ap.add_argument("--mudo", action="store_true", help="sem bipes")
    ap.add_argument("--dormir", type=float, default=120, help="segundos sem eventos até os pets dormirem")
    ap.add_argument("--carinho", type=float, nargs=2, default=(25, 50), metavar=("MIN", "MAX"),
                    help="intervalo (s) entre as cenas de carinho enquanto dormem")
    args = ap.parse_args()

    pygame.init()
    janela = pygame.display.set_mode((args.largura * args.escala, args.altura * args.escala))
    pygame.display.set_caption("pets")
    pets = carregar_pets(args.pets)
    if not pets:
        raise SystemExit("Nenhum pet encontrado em pets/.")
    sim = Simulador(pets, args.largura, args.altura, som=not args.mudo, dormir_s=args.dormir,
                    intervalo_carinho_s=tuple(args.carinho))

    try:
        servidor.iniciar(sim.entrada, [p.id for p in pets], args.porta)
        print(f"Recebendo eventos em http://127.0.0.1:{args.porta}/evento")
    except OSError as e:
        print(f"API HTTP desativada (porta {args.porta}): {e}")

    relogio = pygame.time.Clock()
    proximo_demo = 6000
    progresso_demo, valor_demo = 0, 0
    sim.processar({"evento": "info", "detalhe": "Oi! Estamos de olho em tudo por aqui.", "pet": "ambos"})

    while True:
        dt = relogio.tick(60)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            if ev.type == pygame.KEYDOWN:
                if ev.key in TECLAS:
                    sim.processar(dict(TECLAS[ev.key]))
                elif ev.key == pygame.K_0:
                    sim.processar({"evento": "sucesso", "detalhe": "tudo pronto", "pet": "ambos"})
                elif ev.key == pygame.K_s:
                    destino = RAIZ / "build" / "sim.png"
                    destino.parent.mkdir(exist_ok=True)
                    pygame.image.save(sim.tela, destino)
                    print("captura:", destino)

        if args.demo:
            proximo_demo -= dt
            progresso_demo -= dt
            if progresso_demo <= 0:  # barra avançando em silêncio
                valor_demo = 0 if valor_demo >= 100 else valor_demo + 5
                sim.processar({"evento": "progresso", "detalhe": "migração do banco",
                               "valor": valor_demo, "silencioso": valor_demo < 100})
                progresso_demo = 700
            if proximo_demo <= 0 and sim.atual is None and not sim.fila:
                sim.processar(dict(random.choice(EXEMPLOS)))
                proximo_demo = 6000

        sim.atualizar(dt)
        tela = sim.desenhar()
        pygame.transform.scale(tela, janela.get_size(), janela)
        pygame.display.flip()


if __name__ == "__main__":
    main()
