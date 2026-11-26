"""Fundos de tela das animações especiais, desenhados por código.

Cada fundo é pintado numa grade de baixa resolução (1 ponto = 1 pixel do
sprite) e ampliado pela escala dos pets, para casar com a pixel art.
Os nomes batem com o campo `fundo` de [[extras]] no pet.toml.
"""

from __future__ import annotations

import math
import random

import pygame

Cor = tuple[int, int, int]


def _misturar(a: Cor, b: Cor, t: float) -> Cor:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


class Fundo:
    """Base: guarda a grade em baixa resolução e o cache de quadros."""

    passos = 1       # quadros distintos no ciclo (cache)
    ciclo_ms = 1000

    def __init__(self, w: int, h: int, escala: int, chao: int):
        self.escala = escala
        self.gw, self.gh = math.ceil(w / escala), math.ceil(h / escala)
        self.chao = self.gh - max(1, round(chao / escala))  # linha do chão na grade
        self.w, self.h = w, h
        self._cache: dict[int, pygame.Surface] = {}

    def pintar(self, s: pygame.Surface, fase: float) -> None:  # fase em [0, 1)
        raise NotImplementedError

    def extra(self, s: pygame.Surface, t: int) -> None:
        """Elementos que mudam o tempo todo (desenhados por cima, sem cache)."""

    def desenhar(self, tela: pygame.Surface, t: int) -> None:
        passo = (t * self.passos // self.ciclo_ms) % self.passos
        base = self._cache.get(passo)
        if base is None:
            base = pygame.Surface((self.gw, self.gh))
            self.pintar(base, passo / self.passos)
            self._cache[passo] = base
        s = base.copy()
        self.extra(s, t)
        tela.blit(pygame.transform.scale(s, (self.gw * self.escala, self.gh * self.escala)), (0, 0))


class Espaco(Fundo):
    """Espaço: estrelas cintilando, um planeta com anel, estrela cadente e a Terra lá embaixo."""

    CEU = (10, 12, 30)

    def __init__(self, *a):
        super().__init__(*a)
        rnd = random.Random(7)
        self.estrelas = [
            (rnd.randrange(self.gw), rnd.randrange(self.gh), rnd.random(), rnd.choice((1, 1, 1, 2)))
            for _ in range(self.gw * self.gh // 48)
        ]

    def desenhar(self, tela: pygame.Surface, t: int) -> None:
        s = pygame.Surface((self.gw, self.gh))
        s.fill(self.CEU)
        # Estrelas: cada uma pisca no seu ritmo.
        for x, y, fase, tam in self.estrelas:
            brilho = 0.55 + 0.45 * math.sin(t / 380 + fase * 6.28)
            cor = _misturar(self.CEU, (255, 250, 230), brilho)
            s.set_at((x, y), cor)
            if tam == 2 and brilho > 0.8:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    s.set_at(((x + dx) % self.gw, (y + dy) % self.gh), _misturar(self.CEU, cor, 0.5))

        # Planeta com anel (canto superior direito).
        px, py, r = self.gw - 9, 9, 4
        pygame.draw.ellipse(s, (120, 90, 160), (px - r - 4, py - 1, 2 * r + 9, 3), 1)
        pygame.draw.circle(s, (214, 140, 90), (px, py), r)
        pygame.draw.circle(s, (240, 180, 120), (px - 1, py - 1), r - 2)
        pygame.draw.line(s, (120, 90, 160), (px - r - 3, py + 1), (px + r + 3, py), 1)

        # Terra: curva azul e verde na parte de baixo.
        raio = self.gw * 1.2
        cx, cy = self.gw * 0.5, self.gh + raio - 6
        for y in range(self.gh - 8, self.gh):
            for x in range(self.gw):
                d = math.hypot(x - cx, y - cy)
                if d < raio:
                    terra = math.sin(x * 0.35 + t / 2200) + math.sin(x * 0.13 - y * 0.6) > 0.9
                    cor = (72, 160, 96) if terra else (60, 110, 200)
                    if d > raio - 1:
                        cor = (150, 200, 255)  # atmosfera
                    s.set_at((x, y), cor)

        # Estrela cadente a cada ~4 s.
        ciclo = t % 4200
        if ciclo < 700:
            f = ciclo / 700
            x0, y0 = self.gw * (0.15 + 0.5 * f), self.gh * (0.1 + 0.18 * f)
            for k in range(5):
                c = _misturar((255, 255, 255), self.CEU, k / 5)
                s.set_at((int(x0 - k), int(y0 - k * 0.4)), c)

        tela.blit(pygame.transform.scale(s, (self.gw * self.escala, self.gh * self.escala)), (0, 0))


class NoiteEstrelada(Fundo):
    """Céu em redemoinhos com pinceladas, lua e estrelas com halo, cipreste e colinas,
    numa moldura dourada (homenagem ao estilo de Van Gogh)."""

    passos = 24
    ciclo_ms = 4800
    AZUIS = [(22, 38, 96), (36, 62, 140), (66, 104, 180), (120, 160, 210), (200, 210, 170)]

    def pintar(self, s: pygame.Surface, fase: float) -> None:
        gw, gh = self.gw, self.gh
        ang = fase * 2 * math.pi
        redemoinhos = [(gw * 0.42, gh * 0.30, 1.0), (gw * 0.72, gh * 0.42, -0.8)]
        for y in range(gh):
            for x in range(gw):
                # Pinceladas horizontais onduladas + espirais girando.
                v = math.sin(x * 0.28 + math.sin(y * 0.45 + ang) * 1.6 - ang) * 0.5
                for cx, cy, sentido in redemoinhos:
                    d = math.hypot(x - cx, (y - cy) * 1.3)
                    if d < gw * 0.22:
                        a = math.atan2(y - cy, x - cx)
                        peso = 1 - d / (gw * 0.22)
                        v += math.sin(d * 0.9 - sentido * (a * 2 + ang * 2)) * 1.4 * peso
                textura = ((x * 7 + y * 13) % 5 == 0) * 0.35  # granulado das pinceladas
                i = int(max(0, min(3, (v + 1.2 + textura) / 2.6 * 4)))
                s.set_at((x, y), self.AZUIS[i])

        # Lua crescente com halos pulsando (canto superior direito).
        lx, ly = gw - 10, 8
        pulso = 0.5 + 0.5 * math.sin(ang)
        for r, cor in ((7 + pulso, self.AZUIS[3]), (5.5, (230, 200, 90)), (4, (250, 225, 120))):
            pygame.draw.circle(s, cor, (lx, ly), r)
        pygame.draw.circle(s, (230, 200, 90), (lx + 2, ly - 1), 3)

        # Estrelas com halo amarelo.
        for i, (x, y) in enumerate(((gw * 0.15, gh * 0.12), (gw * 0.30, gh * 0.22),
                                    (gw * 0.60, gh * 0.12), (gw * 0.88, gh * 0.40))):
            p = 0.5 + 0.5 * math.sin(ang + i * 1.7)
            pygame.draw.circle(s, self.AZUIS[3], (int(x), int(y)), 2.5 + p)
            pygame.draw.circle(s, (240, 215, 110), (int(x), int(y)), 1.6)
            s.set_at((int(x), int(y)), (255, 250, 220))

        # Colinas e vilarejo.
        base = self.chao
        for x in range(gw):
            topo = base - 3 - int(2 * math.sin(x * 0.18) + 1.5 * math.sin(x * 0.07 + 1))
            for y in range(max(0, topo), gh):
                verde = (28, 60, 70) if (x + y) % 4 else (40, 80, 90)
                s.set_at((x, y), verde if y < base else (18, 30, 50))
        for i, x in enumerate(range(gw // 2, gw - 4, 5)):  # casinhas com janela acesa
            pygame.draw.rect(s, (46, 56, 84), (x, base - 3, 3, 3))
            if i % 2 == 0:
                s.set_at((x + 1, base - 2), (240, 200, 90))

        # Cipreste: chama escura subindo à esquerda.
        cx = int(gw * 0.12)
        altura = int(gh * 0.62)
        for k in range(altura):
            y = base - k
            meia = max(0, int(3.2 * math.sin(math.pi * (k / altura) ** 0.75)))
            balanco = int(math.sin(k * 0.35 + ang) * 0.8)
            for x in range(cx - meia + balanco, cx + meia + 1 + balanco):
                tom = (20, 46, 34) if (x + k) % 3 else (34, 70, 46)
                if 0 <= x < gw and 0 <= y < gh:
                    s.set_at((x, y), tom)

        # Moldura dourada.
        pygame.draw.rect(s, (150, 104, 40), (0, 0, gw, gh), 2)
        pygame.draw.rect(s, (226, 178, 84), (0, 0, gw, gh), 1)
        pygame.draw.rect(s, (90, 60, 26), (2, 2, gw - 4, gh - 4), 1)


FUNDOS = {"espaco": Espaco, "noite_estrelada": NoiteEstrelada}


def criar(nome: str | None, w: int, h: int, escala: int, chao: int) -> Fundo | None:
    cls = FUNDOS.get(nome or "")
    return cls(w, h, escala, chao) if cls else None
