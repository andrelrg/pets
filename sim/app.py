"""Simulador: tela virtual (ex.: 240x240) com os pets, painel de status, balão de fala e voz.

Layout (se adapta ao tamanho da tela):

    ┌──────────────────────────┐
    │ 14:32          qui 26/11 │  painel: relógio, tarefa em andamento e
    │ migração          60%    │  barra de progresso, último evento.
    │ ▓▓▓▓▓▓▓▓▓▓░░░░░░░        │  (o balão de fala cobre o painel)
    │                          │
    │   [Nala]      [Simba]    │  pets na maior escala inteira que cabe
    │                          │
    └──────────────────────────┘
"""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass, field

import pygame

from .recursos import PetSim
from .voz import Voz

FUNDO = (32, 34, 58)
CHAO = (44, 47, 78)
PAINEL = (44, 47, 78)
PAINEL_TEXTO = (240, 236, 228)
PAINEL_FRACO = (138, 140, 170)
BARRA = (120, 200, 140)
BALAO = (244, 239, 230)
BALAO_BORDA = (26, 18, 22)
TEXTO = (26, 18, 22)
COR_EVENTO = {
    "erro": (230, 90, 90), "aviso": (235, 180, 80), "pendente": (235, 180, 80),
    "sucesso": (120, 200, 140), "marco": (120, 200, 140), "deploy": (130, 170, 240),
}
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

# Evento -> papel do pet que responde quando pet = "auto".
PAPEL_DO_EVENTO = {
    "erro": "alerta", "aviso": "alerta", "pendente": "alerta", "deploy": "alerta",
    "sucesso": "progresso", "progresso": "progresso", "marco": "progresso", "info": "progresso",
}
PRIORIDADE = {"baixa": 0, "normal": 1, "alta": 2}

MARGEM = 6
CHAO_ALTURA = 10
ESPACO_PAINEL = 0.36  # fração mínima da altura reservada ao painel/balão


@dataclass
class Fala:
    pet: PetSim
    texto: str
    evento: str
    prioridade: int = 1
    paginas: list[list[str]] = field(default_factory=list)


@dataclass
class EstadoPet:
    pet: PetSim
    animacao: str = "idle"
    t: int = 0  # ms desde o início da animação atual

    def tocar(self, nome: str) -> None:
        if nome != self.animacao:
            self.animacao, self.t = nome, 0


@dataclass
class Tarefa:
    nome: str
    valor: float | None  # 0-100, ou None se indeterminado
    concluida_em: float | None = None


class Simulador:
    def __init__(self, pets: list[PetSim], largura: int = 240, altura: int = 240, som: bool = True,
                 relogio=time.localtime):
        self.pets = pets
        self.w, self.h = largura, altura
        self.tela = pygame.Surface((largura, altura))
        self.estados = {p.id: EstadoPet(p) for p in pets}
        self.fonte = pygame.font.Font(None, 17)
        self.fonte_pequena = pygame.font.Font(None, 15)
        self.fonte_grande = pygame.font.Font(None, 34)
        self.voz = Voz() if som else None
        self.relogio = relogio
        self.entrada: "queue.Queue[dict]" = queue.Queue()
        self.fila: list[Fala] = []
        self.atual: Fala | None = None
        self.pagina = 0
        self.mostrados = 0.0
        self.espera = 0  # ms parado com a página completa
        self.tarefa: Tarefa | None = None
        self.ultimo: tuple[str, str, str] | None = None  # (evento, detalhe, hora)
        self._montar_layout()

    # --- layout -------------------------------------------------------------

    def _montar_layout(self) -> None:
        """Escolhe a maior escala inteira em que os pets cabem lado a lado,
        deixando espaço em cima para o painel/balão."""
        caixas = [p.caixa for p in self.pets]
        n = len(caixas)
        vao = 8
        alt_max = self.h * (1 - ESPACO_PAINEL) - CHAO_ALTURA
        escala = 1
        for s in range(1, 10):
            larg = sum(c.w for c in caixas) * s + vao * (n - 1) + 2 * MARGEM
            alt = max(c.h for c in caixas) * s
            if larg <= self.w and alt <= alt_max:
                escala = s
        self.escala = escala

        # Distribui os pets com espaços iguais entre eles e nas bordas.
        livre = self.w - sum(c.w for c in caixas) * escala
        passo = livre / (n + 1)
        self.base = self.h - CHAO_ALTURA + 2
        self.posicoes: dict[str, tuple[int, int]] = {}  # id -> (x do quadro, y do quadro)
        x = passo
        for pet in self.pets:
            c = pet.caixa
            self.posicoes[pet.id] = (round(x - c.x * escala), self.base - c.bottom * escala)
            x += c.w * escala + passo
        self.topo_pets = min(self.base - c.h * escala for c in caixas)
        self.area_balao = self.topo_pets - 12  # altura disponível para balão/painel
        alt_linha = self.fonte.get_linesize()
        self.linhas_por_pagina = max(1, min(4, (self.area_balao - MARGEM - 26) // alt_linha))

    def centro_pet(self, pet: PetSim) -> int:
        x, _ = self.posicoes[pet.id]
        return round(x + pet.caixa.centerx * self.escala)

    # --- eventos ------------------------------------------------------------

    def _destinatarios(self, ev: dict) -> list[PetSim]:
        alvo = ev.get("pet", "auto")
        if alvo == "ambos":
            return list(self.pets)
        if alvo != "auto":
            return [p for p in self.pets if p.id == alvo] or self.pets[:1]
        papel = PAPEL_DO_EVENTO.get(ev["evento"], "progresso")
        return [p for p in self.pets if p.papel in (papel, "ambos")][:1] or self.pets[:1]

    def processar(self, ev: dict) -> None:
        evento, detalhe = ev["evento"], ev.get("detalhe", "")
        hora = time.strftime("%H:%M", self.relogio())
        if evento == "progresso":
            valor = ev.get("valor")
            valor = max(0.0, min(100.0, float(valor))) if valor is not None else None
            self.tarefa = Tarefa(ev.get("tarefa") or detalhe or "tarefa", valor)
            if valor is not None and valor >= 100:
                self.tarefa.concluida_em = time.monotonic()
        elif evento == "sucesso" and self.tarefa and self.tarefa.valor is not None:
            self.tarefa.valor, self.tarefa.concluida_em = 100.0, time.monotonic()
        if evento != "progresso" or not ev.get("silencioso"):
            self.ultimo = (evento, detalhe, hora)
        if ev.get("silencioso"):
            return  # só atualiza o painel

        prioridade = PRIORIDADE.get(ev.get("prioridade", "normal"), 1)
        falas = [Fala(pet, pet.fala(evento, detalhe), evento, prioridade) for pet in self._destinatarios(ev)]
        for f in falas:
            f.paginas = self._paginar(f.texto)
        if prioridade == 2:
            # Alta prioridade interrompe a fala atual e passa na frente do resto.
            self.fila = falas + self.fila
            self._encerrar_fala()
        else:
            self.fila.extend(falas)
            self.fila.sort(key=lambda f: -f.prioridade)  # sort estável: mantém a ordem de chegada

    # --- texto --------------------------------------------------------------

    def _paginar(self, texto: str) -> list[list[str]]:
        largura = self.w - 2 * MARGEM - 12
        linhas, atual = [], ""
        for palavra in texto.split():
            tentativa = f"{atual} {palavra}".strip()
            if self.fonte.size(tentativa)[0] <= largura or not atual:
                atual = tentativa
            else:
                linhas.append(atual)
                atual = palavra
        if atual:
            linhas.append(atual)
        n = self.linhas_por_pagina
        return [linhas[i : i + n] for i in range(0, len(linhas), n)] or [[""]]

    def _encerrar_fala(self) -> None:
        if self.atual:
            self.estados[self.atual.pet.id].tocar("idle")
        self.atual = None

    # --- atualização --------------------------------------------------------

    def atualizar(self, dt: int) -> None:
        while not self.entrada.empty():
            self.processar(self.entrada.get())

        for e in self.estados.values():
            e.t += dt
        if self.tarefa and self.tarefa.concluida_em and time.monotonic() - self.tarefa.concluida_em > 8:
            self.tarefa = None

        if self.atual is None and self.fila:
            self.atual = self.fila.pop(0)
            self.pagina, self.mostrados, self.espera = 0, 0.0, 0
            self.estados[self.atual.pet.id].tocar("falando")
        if self.atual is None:
            return

        texto = " ".join(self.atual.paginas[self.pagina])
        voz = self.atual.pet.voz
        if self.mostrados < len(texto):
            antes = int(self.mostrados)
            self.mostrados = min(len(texto), self.mostrados + dt * 0.032 * voz["velocidade"])
            for i in range(antes, int(self.mostrados)):
                ch = texto[i]
                if ch.isalnum() and i % 2 == 0 and self.voz:
                    self.voz.silaba(voz["tom"], enfase=ch.isupper())
            if self.mostrados >= len(texto):
                self.estados[self.atual.pet.id].tocar("idle")
        else:
            self.espera += dt
            if self.espera >= 1400 + 35 * len(texto):
                if self.pagina + 1 < len(self.atual.paginas):
                    self.pagina, self.mostrados, self.espera = self.pagina + 1, 0.0, 0
                    self.estados[self.atual.pet.id].tocar("falando")
                else:
                    self._encerrar_fala()

    # --- desenho ------------------------------------------------------------

    def desenhar(self) -> pygame.Surface:
        t = self.tela
        t.fill(FUNDO)
        pygame.draw.rect(t, CHAO, (0, self.h - CHAO_ALTURA, self.w, CHAO_ALTURA))

        e = self.escala
        for pet in self.pets:
            est = self.estados[pet.id]
            q = pet.animacao(est.animacao).quadro(est.t)
            t.blit(pygame.transform.scale(q, (q.get_width() * e, q.get_height() * e)), self.posicoes[pet.id])

        if self.atual:
            self._desenhar_balao()
        else:
            self._desenhar_painel()
        return t

    def _texto(self, fonte, texto: str, cor, pos, ancora: str = "topleft") -> pygame.Rect:
        s = fonte.render(texto, False, cor)
        r = s.get_rect(**{ancora: pos})
        self.tela.blit(s, r)
        return r

    def _cortar(self, fonte, texto: str, largura: int) -> str:
        if fonte.size(texto)[0] <= largura:
            return texto
        while texto and fonte.size(texto + "…")[0] > largura:
            texto = texto[:-1]
        return texto + "…"

    def _desenhar_painel(self) -> None:
        agora = self.relogio()
        x, y, w = MARGEM + 2, MARGEM, self.w - 2 * (MARGEM + 2)
        r = self._texto(self.fonte_grande, time.strftime("%H:%M", agora), PAINEL_TEXTO, (x, y))
        data = f"{DIAS[agora.tm_wday]} {agora.tm_mday:02d}/{agora.tm_mon:02d}"
        self._texto(self.fonte_pequena, data, PAINEL_FRACO, (x + w, r.bottom - 2), "bottomright")
        y = r.bottom + 6
        limite = self.area_balao

        if self.tarefa and y + 26 <= limite:
            tf = self.tarefa
            valor = tf.valor
            rotulo = "concluído" if tf.concluida_em else (f"{valor:.0f}%" if valor is not None else "…")
            rr = self._texto(self.fonte_pequena, rotulo, PAINEL_TEXTO, (x + w, y), "topright")
            self._texto(self.fonte_pequena, self._cortar(self.fonte_pequena, tf.nome, w - rr.w - 8), PAINEL_TEXTO, (x, y))
            y += self.fonte_pequena.get_linesize() + 2
            pygame.draw.rect(self.tela, PAINEL, (x, y, w, 7), border_radius=2)
            if valor is not None:
                cheio = round((w - 2) * valor / 100)
                if cheio:
                    pygame.draw.rect(self.tela, BARRA, (x + 1, y + 1, cheio, 5), border_radius=2)
            else:  # indeterminado: bloco que corre pela barra
                pos = (pygame.time.get_ticks() // 12) % (w + 30) - 30
                bloco = pygame.Rect(x + 1 + pos, y + 1, 30, 5).clip(pygame.Rect(x + 1, y + 1, w - 2, 5))
                pygame.draw.rect(self.tela, BARRA, bloco, border_radius=2)
            y += 7 + 6

        if self.ultimo and y + self.fonte_pequena.get_linesize() <= limite:
            evento, detalhe, hora = self.ultimo
            cor = COR_EVENTO.get(evento, PAINEL_FRACO)
            pygame.draw.circle(self.tela, cor, (x + 3, y + 6), 3)
            texto = f"{hora} {evento}" + (f": {detalhe}" if detalhe else "")
            self._texto(self.fonte_pequena, self._cortar(self.fonte_pequena, texto, w - 10), PAINEL_FRACO, (x + 10, y))

    def _desenhar_balao(self) -> None:
        f = self.atual
        linhas = f.paginas[self.pagina]
        alt_linha = self.fonte.get_linesize()
        x, w = MARGEM, self.w - 2 * MARGEM
        h = 18 + alt_linha * len(linhas) + 8
        y = max(MARGEM, self.topo_pets - h - 12)

        # Rabicho apontando para o pet que fala.
        bx = max(x + 14, min(x + w - 14, self.centro_pet(f.pet)))
        pygame.draw.polygon(self.tela, BALAO_BORDA, [(bx - 7, y + h - 2), (bx + 7, y + h - 2), (bx, y + h + 10)])
        pygame.draw.polygon(self.tela, BALAO, [(bx - 5, y + h - 3), (bx + 5, y + h - 3), (bx, y + h + 7)])
        pygame.draw.rect(self.tela, BALAO_BORDA, (x - 1, y - 1, w + 2, h + 2), border_radius=7)
        pygame.draw.rect(self.tela, BALAO, (x + 1, y + 1, w - 2, h - 2), border_radius=6)

        cor_nome = f.pet.config["aparencia"]["cores"].get("marca", "#c08a4e")
        self._texto(self.fonte_pequena, f.pet.nome.upper(), pygame.Color(cor_nome), (x + 6, y + 5))

        restante = int(self.mostrados)
        ty = y + 18
        for linha in linhas:
            parte = linha[:restante]
            restante -= len(linha) + 1
            if parte:
                self._texto(self.fonte, parte, TEXTO, (x + 6, ty))
            ty += alt_linha
            if restante <= 0:
                break

        # Indicador de "tem mais" piscando quando a página terminou.
        texto = " ".join(linhas)
        if self.mostrados >= len(texto) and self.pagina + 1 < len(f.paginas) and (self.espera // 300) % 2 == 0:
            ax, ay = x + w - 12, y + h - 9
            pygame.draw.polygon(self.tela, TEXTO, [(ax, ay), (ax + 6, ay), (ax + 3, ay + 4)])
