"""Montagem de um pet: escolhe as partes, compõe as camadas e aplica as cores."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .templates import TRANSPARENTE, Biblioteca, Parte

TAMANHO = 48  # sprite 48x48 (x5 = tela de 240x240)

CORES_FIXAS = {
    "contorno": "#1a1216",
    "brilho": "#ffffff",
    "esclera": "#efe9df",
    "lingua": "#e2788a",
}
COR_SOMBRA = "#2a2040"  # sombra puxada para o roxo (hue shift clássico)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _misturar(a: str, b: str, t: float) -> tuple[int, int, int]:
    ra, rb = _hex(a), _hex(b)
    return tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))  # type: ignore[return-value]


@dataclass
class Pose:
    """Estado de um quadro de animação."""

    olhos: str = "aberto"        # aberto | meio | desconfiado | fechado | feliz
    olhar: tuple[int, int] = (0, 0)  # deslocamento da íris (x, y); x<0 = para a esquerda
    orelha_esq: str = "normal"   # lado esquerdo de quem olha
    orelha_dir: str = "normal"
    rabo: str | None = "a"
    dy_cabeca: int = 0
    boca: str | None = None      # None = fechada | lingua | aberta | entreaberta
    dy: int = 0                  # deslocamento vertical do pet inteiro (pulinho)
    dx_cabeca: int = 0           # cabeça para o lado (inclinação/curiosidade)
    simbolo: str | None = None   # exclamacao | interrogacao | pontos1-3 | z1 | z2 | coracao(_sobe1-3)
    postura: str = "sentado"     # sentado | deitado | em_pe (nas patas de trás)
    duracao: int = 200  # ms


@dataclass
class Pet:
    config: dict
    biblioteca: Biblioteca
    pasta: Path
    partes: dict[str, Parte] = field(default_factory=dict)

    @classmethod
    def carregar(cls, pasta: Path, raiz_templates: Path) -> "Pet":
        with open(pasta / "pet.toml", "rb") as f:
            config = tomllib.load(f)
        especie = config["pet"].get("especie", "cachorro")
        pet = cls(config=config, biblioteca=Biblioteca(raiz_templates / especie), pasta=pasta)
        pet._escolher_partes()
        return pet

    @property
    def id(self) -> str:
        return self.config["pet"]["id"]

    @property
    def nome(self) -> str:
        return self.config["pet"]["nome"]

    @property
    def personalidade(self) -> dict:
        return self.config.get("personalidade", {})

    # --- escolha das partes -------------------------------------------------

    def _escolher_partes(self) -> None:
        ap = self.config["aparencia"]
        b = self.biblioteca
        self.partes["corpo"] = b.parte("corpo", ap.get("corpo", "medio"))
        self.partes["corpo_deitado"] = b.parte("corpo", ap.get("corpo", "medio") + "_deitado")
        em_pe = ap.get("corpo", "medio") + "_em_pe"
        self.partes["corpo_em_pe"] = b.parte("corpo", em_pe) if b.existe("corpo", em_pe) else self.partes["corpo"]
        self.partes["cabeca"] = b.parte("cabeca", ap.get("focinho", "medio"))
        self.partes["olho"] = b.parte("olho", ap.get("olhos", "aberto"))
        self.partes["rabo"] = b.parte("rabo", ap.get("rabo", "padrao"))
        self.partes["boca"] = b.parte("boca", ap.get("boca", "padrao"))
        self.partes["simbolo"] = b.parte("simbolo", "padrao")

        tipo_orelha = ap.get("orelhas", "em_pe")
        orelha = b.parte("orelha", tipo_orelha)
        orelha_pet_dir = orelha_pet_esq = orelha

        # Marca na orelha, ex.: "corte_ponta_direita" -> variante "<tipo>_corte"
        # aplicada na orelha DIREITA DO PET (que aparece à esquerda de quem olha).
        marca = ap.get("orelha_marca")
        if marca:
            *nome_marca, lado = marca.split("_")
            variante = f"{tipo_orelha}_{nome_marca[0]}"
            if b.existe("orelha", variante):
                marcada = b.parte("orelha", variante)
                if lado == "direita":
                    orelha_pet_dir = marcada
                else:
                    orelha_pet_esq = marcada

        # Templates de orelha são desenhados como a orelha à esquerda de quem olha.
        self.partes["orelha_esq"] = orelha_pet_dir
        self.partes["orelha_dir"] = orelha_pet_esq.espelhada()

    # --- cores --------------------------------------------------------------

    def mapa_de_cores(self) -> dict[str, tuple[int, int, int]]:
        ap = self.config["aparencia"]
        cores = ap["cores"]
        leg = self.biblioteca.legenda
        padrao = dict(leg["padroes"][ap.get("padrao", "solido")])
        if ap.get("patas") == "brancas":
            padrao["P"] = "claro"
        if ap.get("sobrancelhas") is False:
            padrao["W"] = padrao["T"]

        papeis = {**CORES_FIXAS, **cores}
        papeis.setdefault("claro", cores["base"])
        papeis.setdefault("nariz", CORES_FIXAS["contorno"])
        papeis.setdefault("olhos", CORES_FIXAS["contorno"])

        mapa: dict[str, tuple[int, int, int]] = {}
        for regiao, papel in {**padrao, **leg["fixas"]}.items():
            cor = papeis[papel]
            mapa[regiao] = _hex(cor)
            mapa[regiao.lower()] = _misturar(cor, COR_SOMBRA, 0.28)
        return mapa

    # --- composição ---------------------------------------------------------

    def _corpo(self, pose: Pose) -> Parte:
        return self.partes[{"deitado": "corpo_deitado", "em_pe": "corpo_em_pe"}.get(pose.postura, "corpo")]

    def _origens(self, pose: Pose) -> tuple[int, int, int, int]:
        """Canto superior esquerdo do corpo (cx, cy) e da cabeça (hx, hy) no quadro."""
        corpo = self._corpo(pose)
        cabeca = self.partes["cabeca"]
        cx = (TAMANHO - corpo.largura) // 2
        cy = TAMANHO - corpo.altura + pose.dy
        px, py = corpo.ancoras["pescoco"]
        qx, qy = cabeca.ancoras["queixo"]
        return cx, cy, cx + px - qx + pose.dx_cabeca, cy + py - qy + pose.dy_cabeca

    def pontos(self, pose: Pose) -> dict[str, tuple[int, int]]:
        """Pontos de referência no quadro (para cenas: onde está a boca, as orelhas...)."""
        _, _, hx, hy = self._origens(pose)
        cab = self.partes["cabeca"]
        bx, by = cab.ancoras.get("boca", (cab.largura // 2 - 3, cab.altura - 3))
        ox, oy = cab.ancoras["orelha_esq"]
        dx, dy = cab.ancoras["orelha_dir"]
        return {
            "cabeca": (hx + cab.largura // 2, hy + cab.altura // 2),
            "boca": (hx + bx + 3, hy + by + 1),
            "orelha_esq": (hx + ox, hy + oy),
            "orelha_dir": (hx + dx, hy + dy),
        }

    def compor(self, pose: Pose) -> list[list[str]]:
        """Compõe as camadas numa grade de regiões (TAMANHO x TAMANHO)."""
        tela = [[TRANSPARENTE] * TAMANHO for _ in range(TAMANHO)]

        def carimbar(parte: Parte, quadro: str, x: int, y: int) -> None:
            for j, linha in enumerate(parte.quadro(quadro)):
                for i, ch in enumerate(linha):
                    if ch != TRANSPARENTE and 0 <= x + i < TAMANHO and 0 <= y + j < TAMANHO:
                        tela[y + j][x + i] = ch

        corpo = self._corpo(pose)
        cabeca, olho = self.partes["cabeca"], self.partes["olho"]
        cx, cy, hx, hy = self._origens(pose)

        # Ordem das camadas: rabo, orelhas, corpo, cabeça, olhos.
        if pose.rabo:
            rabo = self.partes["rabo"]
            rx, ry = corpo.ancoras["rabo"]
            bx, by = rabo.ancoras["base"]
            carimbar(rabo, pose.rabo, cx + rx - bx, cy + ry - by)

        for lado, estado in (("esq", pose.orelha_esq), ("dir", pose.orelha_dir)):
            orelha = self.partes[f"orelha_{lado}"]
            ax, ay = cabeca.ancoras[f"orelha_{lado}"]
            bx, by = orelha.ancoras["base"]
            carimbar(orelha, estado, hx + ax - bx, hy + ay - by)

        carimbar(corpo, "normal", cx, cy)
        carimbar(cabeca, "normal", hx, hy)
        if pose.boca:
            bx, by = cabeca.ancoras["boca"]
            carimbar(self.partes["boca"], pose.boca, hx + bx, hy + by)

        if pose.simbolo:
            sx, sy = cabeca.ancoras.get("simbolo", (-10, -10))
            carimbar(self.partes["simbolo"], pose.simbolo, hx + sx, hy + sy)

        for lado in ("esq", "dir"):
            ox, oy = cabeca.ancoras[f"olho_{lado}"]
            grade = compor_olho(olho, pose.olhos, pose.olhar, espelhar=(lado == "dir"))
            for j, linha in enumerate(grade):
                for i, ch in enumerate(linha):
                    if ch != TRANSPARENTE:
                        tela[hy + oy + j][hx + ox + i] = ch
        return tela


def compor_olho(olho: Parte, estado: str, olhar: tuple[int, int], espelhar: bool) -> list[str]:
    """Olho em camadas: forma (contorno + branco), íris deslocada, pálpebra.

    Na pálpebra, "-" apaga o olho (mostra o pelo da cabeça por baixo).
    """
    forma = [list(l) for l in olho.quadros["forma"]]
    if espelhar:
        forma = [l[::-1] for l in forma]
    w = len(forma[0])

    iris = olho.quadros["iris"]
    ix, iy = olho.ancoras.get("iris", (0, 0))
    if espelhar:
        ix = w - (ix + len(iris[0]))
    ix, iy = ix + olhar[0], iy + olhar[1]
    branco = {(x, y) for y, l in enumerate(forma) for x, ch in enumerate(l) if ch == "Z"}
    for j, linha in enumerate(iris):
        for i, ch in enumerate(linha):
            if ch != TRANSPARENTE and (ix + i, iy + j) in branco:
                forma[iy + j][ix + i] = ch

    if estado != "aberto" and estado in olho.quadros:
        palpebra = olho.quadros[estado]
        if espelhar:
            palpebra = [l[::-1] for l in palpebra]
        for j, linha in enumerate(palpebra):
            for i, ch in enumerate(linha):
                if ch == "-":
                    forma[j][i] = TRANSPARENTE
                elif ch != TRANSPARENTE:
                    forma[j][i] = ch
    return ["".join(l) for l in forma]
