"""Voz 8-bit: bipes de onda quadrada sintetizados (sem arquivos de áudio)."""

from __future__ import annotations

import array
import random

import pygame

TAXA = 22050


class Voz:
    def __init__(self) -> None:
        self.ativa = False
        try:
            pygame.mixer.init(frequency=TAXA, size=-16, channels=1)
            self.canal = pygame.mixer.Channel(0)
            self.ativa = True
        except pygame.error:
            pass
        self._cache: dict[int, pygame.mixer.Sound] = {}

    def _bipe(self, freq: int, ms: int = 45, volume: float = 0.18) -> "pygame.mixer.Sound":
        chave = freq * 1000 + ms
        if chave not in self._cache:
            n = int(TAXA * ms / 1000)
            periodo = max(2, int(TAXA / freq))
            amp = int(32767 * volume)
            amostras = array.array("h")
            for i in range(n):
                env = min(1.0, i / 60, (n - i) / 200)  # ataque/soltura curtos (sem estalo)
                amostras.append(int(amp * env) if (i % periodo) < periodo // 2 else -int(amp * env))
            self._cache[chave] = pygame.mixer.Sound(buffer=amostras.tobytes())
        return self._cache[chave]

    def silaba(self, tom: float = 1.0, enfase: bool = False) -> None:
        if not self.ativa:
            return
        base = 440 * tom * (1.15 if enfase else 1.0)
        freq = int(base * random.uniform(0.88, 1.12) / 10) * 10
        self.canal.play(self._bipe(freq))
