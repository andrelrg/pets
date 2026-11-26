"""Carregamento dos templates de pixel art em texto.

Formato de um arquivo de parte (.txt):

    # comentário
    @ancora nome x y        (vale para todos os quadros)
    === nome_do_quadro      (opcional; sem isso, o quadro se chama "normal")
    ..OO..
    .OXXO.

Cada caractere é uma região (ver legenda.toml); "." é transparente.
Quadros podem ter tamanhos diferentes (ex.: a íris do olho); largura/altura
da parte são as do primeiro quadro.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

TRANSPARENTE = "."


@dataclass
class Parte:
    nome: str
    quadros: dict[str, list[str]]
    ancoras: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def largura(self) -> int:
        return len(next(iter(self.quadros.values()))[0])

    @property
    def altura(self) -> int:
        return len(next(iter(self.quadros.values())))

    def quadro(self, nome: str) -> list[str]:
        """Retorna o quadro pedido, ou "normal"/o primeiro se não existir."""
        if nome in self.quadros:
            return self.quadros[nome]
        if "normal" in self.quadros:
            return self.quadros["normal"]
        return next(iter(self.quadros.values()))

    def espelhada(self) -> "Parte":
        w = self.largura
        return Parte(
            nome=self.nome + "~espelho",
            quadros={k: [linha[::-1] for linha in q] for k, q in self.quadros.items()},
            ancoras={k: (w - 1 - x, y) for k, (x, y) in self.ancoras.items()},
        )


def carregar_parte(caminho: Path) -> Parte:
    quadros: dict[str, list[str]] = {}
    ancoras: dict[str, tuple[int, int]] = {}
    atual = "normal"
    for bruta in caminho.read_text(encoding="utf-8").splitlines():
        linha = bruta.rstrip()
        if not linha or linha.startswith("#"):
            continue
        if linha.startswith("@"):
            nome, x, y = linha[1:].split()
            ancoras[nome] = (int(x), int(y))
        elif linha.startswith("==="):
            atual = linha[3:].strip()
            quadros[atual] = []
        else:
            quadros.setdefault(atual, []).append(linha)

    for nome, q in quadros.items():
        larguras = {len(l) for l in q}
        if len(larguras) != 1:
            raise ValueError(f"{caminho} [{nome}]: linhas com larguras diferentes {larguras}")
    return Parte(nome=caminho.stem, quadros=quadros, ancoras=ancoras)


class Biblioteca:
    """Conjunto de templates de uma espécie (ex.: art/templates/cachorro)."""

    def __init__(self, raiz: Path):
        self.raiz = raiz
        with open(raiz / "legenda.toml", "rb") as f:
            self.legenda = tomllib.load(f)

    def parte(self, tipo: str, variante: str) -> Parte:
        caminho = self.raiz / tipo / f"{variante}.txt"
        if not caminho.exists():
            disponiveis = sorted(p.stem for p in (self.raiz / tipo).glob("*.txt"))
            raise FileNotFoundError(
                f"Template '{tipo}/{variante}' não existe. Disponíveis: {disponiveis}"
            )
        return carregar_parte(caminho)

    def existe(self, tipo: str, variante: str) -> bool:
        return (self.raiz / tipo / f"{variante}.txt").exists()
