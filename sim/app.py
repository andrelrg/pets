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
import random
import time
from dataclasses import dataclass, field

import pygame

from . import fundos
from .fonte import FontePixel
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

# Reação (animação) antes da fala, por evento.
REACAO = {
    "erro": "alerta", "aviso": "alerta", "pendente": "alerta", "deploy": "alerta",
    "sucesso": "feliz", "marco": "feliz", "progresso": "pensando", "info": "curioso",
}

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
    t: int = 0              # ms desde o início da animação atual
    ate: int | None = None  # animação temporária: ms até voltar ao estado base
    dx: float = 0.0         # deslocamento na tela (cenas)
    dy: float = 0.0

    def tocar(self, nome: str, por: int | None = None) -> None:
        if nome != self.animacao:
            self.animacao, self.t = nome, 0
        self.ate = por


@dataclass
class Passo:
    inicio: int
    fim: int
    pet: str
    animacao: str
    dx: tuple[float, float] = (0.0, 0.0)  # deslocamento no início e no fim do passo
    dy: tuple[float, float] = (0.0, 0.0)


@dataclass
class Cena:
    """Coreografia de vários pets numa linha do tempo."""
    nome: str
    passos: list[Passo]
    frente: str | None = None  # pet desenhado por cima
    t: int = 0

    @property
    def duracao(self) -> int:
        return max(p.fim for p in self.passos)

    @property
    def pets(self) -> set[str]:
        return {p.pet for p in self.passos}


def _suave(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


@dataclass
class Especial:
    """Animação especial em andamento (extras do pet.toml): fundo próprio, só o pet em cena."""
    pet: str
    animacao: str
    fundo: "fundos.Fundo | None"
    t: int = 0

    @property
    def falando(self) -> str:
        return f"{self.animacao}_falando"

    @property
    def loop(self) -> str:
        return f"{self.animacao}_loop"


@dataclass
class Tarefa:
    nome: str
    valor: float | None  # 0-100, ou None se indeterminado
    concluida_em: float | None = None


class Simulador:
    def __init__(self, pets: list[PetSim], largura: int = 240, altura: int = 240, som: bool = True,
                 relogio=time.localtime, dormir_s: float = 120,
                 intervalo_carinho_s: tuple[float, float] = (25, 50)):
        self.pets = pets
        self.w, self.h = largura, altura
        self.tela = pygame.Surface((largura, altura))
        self.estados = {p.id: EstadoPet(p) for p in pets}
        # Fonte pixel em 2x: em 1x as letras teriam <1 mm numa tela de 1,5".
        self.fonte = FontePixel(2)
        self.fonte_grande = FontePixel(3)
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
        self.dormir_ms = int(dormir_s * 1000)
        self.ocioso = 0       # ms sem nenhum evento
        self.reagindo = 0     # ms restantes da reação antes da fala começar
        self.cena: Cena | None = None
        self.especial: Especial | None = None
        self.intervalo_carinho = intervalo_carinho_s
        self.ate_carinho = self._sortear_carinho()
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
        self.linhas_por_pagina = max(1, min(4, (self.area_balao - MARGEM - 8) // self.fonte.get_linesize()))

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
        self.ocioso = 0
        self._cancelar_cena()
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
        largura = self.w - 2 * MARGEM - 14
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
            self.estados[self.atual.pet.id].tocar(self.estado_base(self.atual.pet))
        self.atual = None
        self.reagindo = 0
        self.especial = None

    # --- cenas --------------------------------------------------------------

    def _sortear_carinho(self) -> int:
        return int(random.uniform(*self.intervalo_carinho) * 1000)

    def cena_carinho(self) -> Cena | None:
        """Enquanto dormem: o pet mais enérgico acorda, vai até o mais carinhoso,
        lambe a orelha dele (que fica feliz) e volta a dormir."""
        if len(self.pets) < 2:
            return None

        def traco(p: PetSim, nome: str) -> float:
            return p.config.get("personalidade", {}).get(nome, 0.5)

        ativo = max(self.pets, key=lambda p: traco(p, "energia"))
        passivo = max((p for p in self.pets if p is not ativo), key=lambda p: traco(p, "carinho"))
        precisa = {"acordando_esq", "acordando_dir", "andando", "lambendo_esq", "lambendo_dir"}
        if not precisa <= set(ativo.animacoes) or "deitado_feliz" not in passivo.animacoes:
            return None

        e = self.escala
        sentido = -1 if self.centro_pet(passivo) < self.centro_pet(ativo) else 1
        lado = "esq" if sentido < 0 else "dir"
        # O ativo fica ATRÁS do passivo, com a boca na ponta da orelha
        # virada para ele: o rosto dos dois fica visível e o corpo do ativo se esconde.
        ox, oy = passivo.pontos["deitado_feliz"]["orelha_dir" if sentido < 0 else "orelha_esq"]
        ox, oy = ox - sentido * 5, oy - 7  # ponta da orelha caída
        bx, by = ativo.pontos[f"lambendo_{lado}"]["boca"]
        (px, py), (ax, ay) = self.posicoes[passivo.id], self.posicoes[ativo.id]
        alvo_x = (px + ox * e) - (ax + bx * e)
        alvo_y = min(0, (py + oy * e) - (ay + by * e))  # só sobe, nunca desce

        a, b = ativo.id, passivo.id
        return Cena("carinho", frente=b, passos=[
            Passo(0, 1500, a, f"acordando_{lado}"),
            Passo(1500, 2900, a, "andando", (0, alvo_x), (0, alvo_y)),
            Passo(2900, 5900, a, f"lambendo_{lado}", (alvo_x, alvo_x), (alvo_y, alvo_y)),
            Passo(3300, 6700, b, "deitado_feliz"),
            Passo(5900, 7300, a, "andando", (alvo_x, 0), (alvo_y, 0)),
        ])

    def _cancelar_cena(self) -> None:
        if self.cena:
            for pid in self.cena.pets:
                est = self.estados[pid]
                est.dx = est.dy = 0.0
                est.tocar(self.estado_base(est.pet))
        self.cena = None

    def _atualizar_cena(self, dt: int) -> None:
        c = self.cena
        c.t += dt
        if c.t >= c.duracao:
            self._cancelar_cena()
            return
        for pid in c.pets:
            atuais = [p for p in c.passos if p.pet == pid and p.inicio <= c.t < p.fim]
            est = self.estados[pid]
            if atuais:
                p = atuais[-1]
                est.tocar(p.animacao, por=p.fim - c.t + 50)
                f = _suave((c.t - p.inicio) / max(1, p.fim - p.inicio))
                est.dx = p.dx[0] + (p.dx[1] - p.dx[0]) * f
                est.dy = p.dy[0] + (p.dy[1] - p.dy[0]) * f
            else:
                est.dx = est.dy = 0.0
                est.tocar(self.estado_base(est.pet))

    def estado_base(self, pet: PetSim) -> str:
        """Animação de fundo: dormindo (ocioso), pensando (tarefa em andamento) ou idle."""
        if self.ocioso >= self.dormir_ms:
            return "dormindo"
        tarefa_ativa = self.tarefa is not None and self.tarefa.concluida_em is None
        if tarefa_ativa and pet.papel in ("progresso", "ambos"):
            return "pensando"
        return "idle"

    def _extra(self, pet: PetSim, evento: str) -> dict | None:
        """Animação especial do pet disparada por este evento, se houver."""
        for x in pet.config.get("extras", []):
            nome = f"extra_{x.get('id')}"
            if x.get("gatilho") == evento and {nome, f"{nome}_falando", f"{nome}_loop"} <= set(pet.animacoes):
                return x
        return None

    def _anim_falando(self) -> str:
        return self.especial.falando if self.especial else "falando"

    def _iniciar_fala(self, fala: Fala) -> None:
        self.atual = fala
        self.pagina, self.mostrados, self.espera = 0, 0.0, 0
        self.especial = None
        est = self.estados[fala.pet.id]
        reacao = REACAO.get(fala.evento)
        extra = self._extra(fala.pet, fala.evento)
        if extra:
            nome = f"extra_{extra['id']}"
            fundo = fundos.criar(extra.get("fundo"), self.w, self.h, self.escala, CHAO_ALTURA)
            self.especial = Especial(fala.pet.id, nome, fundo)
            est.tocar(nome)
            self.reagindo = min(fala.pet.animacoes[nome].total, 4000)
            return
        if reacao and reacao in fala.pet.animacoes:
            est.tocar(reacao)
            self.reagindo = min(fala.pet.animacoes[reacao].total, 1800)
        else:
            est.tocar("falando")
            self.reagindo = 0
        # Os outros pets olham, curiosos, quando alguém dá um alerta.
        if reacao == "alerta":
            for outro in self.pets:
                if outro is not fala.pet:
                    self.estados[outro.id].tocar("curioso", por=1600)

    # --- atualização --------------------------------------------------------

    def atualizar(self, dt: int) -> None:
        while not self.entrada.empty():
            self.processar(self.entrada.get())

        if self.tarefa and self.tarefa.concluida_em and time.monotonic() - self.tarefa.concluida_em > 8:
            self.tarefa = None
        if self.atual is None and not self.fila:
            self.ocioso += dt

        # Cena de carinho de tempos em tempos enquanto todos dormem.
        if self.cena:
            self._atualizar_cena(dt)
        elif self.atual is None and all(self.estado_base(p) == "dormindo" for p in self.pets):
            self.ate_carinho -= dt
            if self.ate_carinho <= 0:
                self.ate_carinho = self._sortear_carinho()
                self.cena = self.cena_carinho()

        if self.atual is None and self.fila:
            self._iniciar_fala(self.fila.pop(0))

        falante = self.atual.pet.id if self.atual else None
        em_cena = self.cena.pets if self.cena else set()
        for e in self.estados.values():
            e.t += dt
            if e.pet.id in em_cena:
                continue
            if e.ate is not None:
                e.ate -= dt
                if e.ate <= 0:
                    e.tocar(self.estado_base(e.pet))
            elif e.pet.id != falante:
                e.tocar(self.estado_base(e.pet))  # acompanha mudanças (tarefa, sono)

        if self.atual is None:
            return
        if self.especial:
            self.especial.t += dt
        if self.reagindo > 0:
            self.reagindo -= dt
            if self.reagindo <= 0:
                self.estados[falante].tocar(self._anim_falando())
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
                fim = self.especial.loop if self.especial else self.estado_base(self.atual.pet)
                self.estados[self.atual.pet.id].tocar(fim)
        else:
            self.espera += dt
            if self.espera >= 1400 + 35 * len(texto):
                if self.pagina + 1 < len(self.atual.paginas):
                    self.pagina, self.mostrados, self.espera = self.pagina + 1, 0.0, 0
                    self.estados[self.atual.pet.id].tocar(self._anim_falando())
                else:
                    self._encerrar_fala()

    # --- desenho ------------------------------------------------------------

    def desenhar(self) -> pygame.Surface:
        t = self.tela
        esp = self.especial
        if esp and esp.fundo:
            esp.fundo.desenhar(t, esp.t)
        else:
            t.fill(FUNDO)
            pygame.draw.rect(t, CHAO, (0, self.h - CHAO_ALTURA, self.w, CHAO_ALTURA))

        e = self.escala
        ordem = sorted(self.pets, key=lambda p: bool(self.cena and self.cena.frente == p.id))
        for pet in ordem:
            if esp and pet.id != esp.pet:
                continue  # momento especial: só o pet dele em cena, centralizado
            est = self.estados[pet.id]
            q = pet.animacao(est.animacao).quadro(est.t)
            x, y = self.posicoes[pet.id]
            dx = self.w // 2 - self.centro_pet(pet) if esp else round(est.dx)
            t.blit(pygame.transform.scale(q, (q.get_width() * e, q.get_height() * e)), (x + dx, y + round(est.dy)))

        if self.atual and self.reagindo <= 0:
            self._desenhar_balao()
        elif not esp:
            self._desenhar_painel()
        return t

    def _texto(self, fonte: FontePixel, texto: str, cor, x: int, y: int, direita: bool = False) -> pygame.Rect:
        """Escreve com (x, y) = canto superior das maiúsculas; devolve a caixa visível."""
        s = fonte.render(texto, False, cor)
        if direita:
            x -= s.get_width()
        self.tela.blit(s, (x, y - fonte.topo))
        return pygame.Rect(x, y, s.get_width(), fonte.altura_maiuscula)

    def _cortar(self, fonte, texto: str, largura: int) -> str:
        if fonte.size(texto)[0] <= largura:
            return texto
        while texto and fonte.size(texto + "…")[0] > largura:
            texto = texto[:-1]
        return texto + "…"

    def _desenhar_painel(self) -> None:
        agora = self.relogio()
        f = self.fonte
        x, y, w = MARGEM + 2, MARGEM + 2, self.w - 2 * (MARGEM + 2)
        r = self._texto(self.fonte_grande, time.strftime("%H:%M", agora), PAINEL_TEXTO, x, y)
        data = f"{DIAS[agora.tm_wday]} {agora.tm_mday:02d}/{agora.tm_mon:02d}"
        self._texto(f, data, PAINEL_FRACO, x + w, r.bottom - f.altura_maiuscula, direita=True)
        y = r.bottom + 8
        limite = self.area_balao

        if self.tarefa and y + f.altura_maiuscula + 11 <= limite:
            tf = self.tarefa
            valor = tf.valor
            rotulo = "ok!" if tf.concluida_em else (f"{valor:.0f}%" if valor is not None else "…")
            rr = self._texto(f, rotulo, PAINEL_TEXTO, x + w, y, direita=True)
            self._texto(f, self._cortar(f, tf.nome, w - rr.w - 8), PAINEL_TEXTO, x, y)
            y += f.altura_maiuscula + 4
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

        if self.ultimo and y + f.altura_maiuscula <= limite:
            evento, detalhe, hora = self.ultimo
            cor = COR_EVENTO.get(evento, PAINEL_FRACO)
            pygame.draw.rect(self.tela, cor, (x, y + 4, 6, 6))
            texto = f"{hora} {detalhe or evento}"
            self._texto(f, self._cortar(f, texto, w - 10), PAINEL_FRACO, x + 10, y)

    def _desenhar_balao(self) -> None:
        f = self.atual
        linhas = f.paginas[self.pagina]
        alt_linha = self.fonte.get_linesize()
        x, w = MARGEM, self.w - 2 * MARGEM
        h = 8 + alt_linha * len(linhas)
        y = max(MARGEM, self.topo_pets - h - 12)

        # Rabicho apontando para o pet que fala.
        bx = max(x + 14, min(x + w - 14, self.centro_pet(f.pet)))
        pygame.draw.polygon(self.tela, BALAO_BORDA, [(bx - 7, y + h - 2), (bx + 7, y + h - 2), (bx, y + h + 10)])
        pygame.draw.polygon(self.tela, BALAO, [(bx - 5, y + h - 3), (bx + 5, y + h - 3), (bx, y + h + 7)])
        pygame.draw.rect(self.tela, BALAO_BORDA, (x - 1, y - 1, w + 2, h + 2), border_radius=7)
        pygame.draw.rect(self.tela, BALAO, (x + 1, y + 1, w - 2, h - 2), border_radius=6)

        restante = int(self.mostrados)
        ty = y + 6
        for linha in linhas:
            parte = linha[:restante]
            restante -= len(linha) + 1
            if parte:
                self._texto(self.fonte, parte, TEXTO, x + 7, ty)
            ty += alt_linha
            if restante <= 0:
                break

        # Indicador de "tem mais" piscando quando a página terminou.
        texto = " ".join(linhas)
        if self.mostrados >= len(texto) and self.pagina + 1 < len(f.paginas) and (self.espera // 300) % 2 == 0:
            ax, ay = x + w - 12, y + h - 8
            pygame.draw.polygon(self.tela, TEXTO, [(ax, ay), (ax + 6, ay), (ax + 3, ay + 3)])
