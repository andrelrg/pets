"""Renderização da fonte pixel no pygame (mesma interface básica de pygame.font.Font)."""

from __future__ import annotations

import pygame

from tools.pixelfont import ALTURA, TOPO, carregar

from .recursos import RAIZ

_GLIFOS: dict[str, list[str]] | None = None


def _glifos() -> dict[str, list[str]]:
    global _GLIFOS
    if _GLIFOS is None:
        _GLIFOS = carregar(RAIZ / "art" / "fontes" / "pixel5x7.txt")
    return _GLIFOS


class FontePixel:
    ESPACAMENTO = 1  # colunas entre letras

    def __init__(self, escala: int = 2):
        self.escala = escala
        self.glifos = _glifos()
        self._cache: dict[tuple, pygame.Surface] = {}

    def _glifo(self, ch: str) -> list[str]:
        return self.glifos.get(ch) or self.glifos.get(ch.lower()) or self.glifos["?"]

    def size(self, texto: str) -> tuple[int, int]:
        if not texto:
            return 0, ALTURA * self.escala
        colunas = sum(len(self._glifo(c)[0]) for c in texto) + self.ESPACAMENTO * (len(texto) - 1)
        return colunas * self.escala, ALTURA * self.escala

    def get_linesize(self) -> int:
        return (ALTURA - 1) * self.escala

    @property
    def topo(self) -> int:
        """Pixels vazios acima da altura das maiúsculas (espaço dos acentos)."""
        return TOPO * self.escala

    @property
    def altura_maiuscula(self) -> int:
        return 7 * self.escala

    def render(self, texto: str, _aa: bool, cor) -> pygame.Surface:
        chave = (texto, tuple(pygame.Color(cor)))
        if chave in self._cache:
            return self._cache[chave]
        w, h = self.size(texto)
        base = pygame.Surface((max(1, w // self.escala), ALTURA), pygame.SRCALPHA)
        x = 0
        for ch in texto:
            g = self._glifo(ch)
            for y, linha in enumerate(g):
                for i, px in enumerate(linha):
                    if px == "#":
                        base.set_at((x + i, y), cor)
            x += len(g[0]) + self.ESPACAMENTO
        s = pygame.transform.scale(base, (max(1, w), h))
        if len(self._cache) > 256:
            self._cache.clear()
        self._cache[chave] = s
        return s
