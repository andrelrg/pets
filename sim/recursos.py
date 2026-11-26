"""Carrega pets para o simulador: gera os sprites e lê config + falas."""

from __future__ import annotations

import random
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from tools.petgen.exportar import exportar_pet
from tools.petgen.pet import Pet as PetGen

RAIZ = Path(__file__).resolve().parents[1]

FALAS_PADRAO = {
    "erro": ["Deu erro: {detalhe}."],
    "aviso": ["Atenção: {detalhe}."],
    "sucesso": ["Pronto! {detalhe}."],
    "progresso": ["{detalhe}..."],
    "pendente": ["Falta: {detalhe}."],
    "marco": ["Uhul! {detalhe}!"],
    "deploy": ["Deploy: {detalhe}."],
    "info": ["{detalhe}"],
}


@dataclass
class Animacao:
    quadros: list[pygame.Surface]
    duracoes: list[int]

    @property
    def total(self) -> int:
        return sum(self.duracoes)

    def quadro(self, t_ms: int, loop: bool = True) -> pygame.Surface:
        t = t_ms % self.total if loop else min(t_ms, self.total - 1)
        for q, d in zip(self.quadros, self.duracoes):
            if t < d:
                return q
            t -= d
        return self.quadros[-1]


@dataclass
class PetSim:
    id: str
    nome: str
    config: dict
    falas: dict[str, list[str]]
    animacoes: dict[str, Animacao] = field(default_factory=dict)
    caixa: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 48, 48))  # área usada do quadro

    @property
    def papel(self) -> str:
        return self.config.get("personalidade", {}).get("papel", "ambos")

    @property
    def voz(self) -> dict:
        return {"tom": 1.0, "velocidade": 1.0, **self.config.get("voz", {})}

    def animacao(self, nome: str) -> Animacao:
        return self.animacoes.get(nome) or self.animacoes["idle"]

    def fala(self, evento: str, detalhe: str = "") -> str:
        opcoes = self.falas.get(evento) or FALAS_PADRAO.get(evento) or ["{detalhe}"]
        if not detalhe:
            sem = [o for o in opcoes if "{detalhe}" not in o]
            opcoes = sem or opcoes
        texto = " ".join(random.choice(opcoes).replace("{detalhe}", detalhe).split())
        for p in ".!?,:":
            texto = texto.replace(" " + p, p)
        return texto


def _para_surface(img) -> pygame.Surface:
    return pygame.image.frombytes(img.tobytes(), img.size, "RGBA").convert_alpha()


def carregar_pets(ids: list[str] | None = None) -> list[PetSim]:
    """Gera os sprites (em memória + build/) e monta os pets do simulador."""
    pastas = sorted(p for p in (RAIZ / "pets").iterdir() if (p / "pet.toml").exists())
    if ids:
        pastas = [p for p in pastas if p.name in ids]
    pets = []
    for pasta in pastas:
        gen = PetGen.carregar(pasta, RAIZ / "art" / "templates")
        r = exportar_pet(gen, RAIZ / "build", previews=False)
        falas = {}
        if (pasta / "falas.toml").exists():
            with open(pasta / "falas.toml", "rb") as f:
                falas = tomllib.load(f).get("falas", {})
        pet = PetSim(id=gen.id, nome=gen.nome, config=gen.config, falas=falas)
        superficies = [_para_surface(q) for q in r.quadros]
        for nome, (a, b) in r.tags.items():
            pet.animacoes[nome] = Animacao(superficies[a : b + 1], r.duracoes[a : b + 1])
        caixas = [q.get_bounding_rect() for q in superficies]
        pet.caixa = caixas[0].unionall(caixas[1:])
        pets.append(pet)
    return pets
