"""Gerador de sprites dos pets.

Uso (na raiz do repositório):
    python -m tools.petgen                 # gera todos os pets em pets/
    python -m tools.petgen simba nala      # só os pets indicados
    python -m tools.petgen --escala 10     # escala dos previews

Saídas em build/:
    sprites/<id>.png  + <id>.json   spritesheet 48x48 + metadados (formato Aseprite)
    preview/<id>_<anim>.gif         preview ampliado de cada animação
    preview/todos.gif / todos.png   os pets lado a lado
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .exportar import exportar_pet, preview_conjunto
from .pet import Pet

RAIZ = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser(prog="petgen", description=__doc__.splitlines()[0])
    ap.add_argument("pets", nargs="*", help="ids dos pets (padrão: todos em pets/)")
    ap.add_argument("--escala", type=int, default=8)
    ap.add_argument("--saida", type=Path, default=RAIZ / "build")
    args = ap.parse_args()

    pastas = sorted(p for p in (RAIZ / "pets").iterdir() if (p / "pet.toml").exists())
    if args.pets:
        pastas = [p for p in pastas if p.name in args.pets]
    pets = [Pet.carregar(p, RAIZ / "art" / "templates") for p in pastas]

    resultados = [exportar_pet(pet, args.saida, args.escala) for pet in pets]
    for r in resultados:
        print(f"{r.pet.nome:>8}: {r.n_quadros} quadros, {r.n_cores} cores -> {r.png}")
        if r.n_cores > 16:
            print(f"          aviso: paleta com {r.n_cores} cores (> 16)")
    if len(resultados) > 1:
        print("preview:", preview_conjunto(resultados, args.saida, args.escala))


if __name__ == "__main__":
    main()
