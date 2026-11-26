"""Exportação: spritesheet PNG + JSON (formato Aseprite) e previews GIF/PNG."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .animacoes import animacoes_do_pet
from .pet import TAMANHO, Pet, Pose

FUNDO = (32, 34, 58)


@dataclass
class Resultado:
    pet: Pet
    png: Path
    quadros: list[Image.Image]
    duracoes: list[int]
    tags: dict[str, tuple[int, int]] = field(default_factory=dict)
    pontos: dict[str, dict[str, tuple[int, int]]] = field(default_factory=dict)

    @property
    def n_quadros(self) -> int:
        return len(self.quadros)

    @property
    def n_cores(self) -> int:
        cores = set()
        for q in self.quadros:
            cores |= {c for c in q.getdata() if c[3]}
        return len(cores)


def renderizar(pet: Pet, pose: Pose, cores: dict) -> Image.Image:
    img = Image.new("RGBA", (TAMANHO, TAMANHO), (0, 0, 0, 0))
    px = img.load()
    for y, linha in enumerate(pet.compor(pose)):
        for x, ch in enumerate(linha):
            if ch != ".":
                if ch not in cores:
                    raise ValueError(f"{pet.id}: região '{ch}' sem cor definida")
                px[x, y] = (*cores[ch], 255)
    return img


def _ampliar(img: Image.Image, escala: int, fundo=FUNDO) -> Image.Image:
    base = Image.new("RGBA", img.size, (*fundo, 255))
    base.alpha_composite(img)
    return base.resize((img.width * escala, img.height * escala), Image.NEAREST).convert("RGB")


def _salvar_gif(quadros: list[Image.Image], duracoes: list[int], caminho: Path) -> None:
    # Junta quadros idênticos consecutivos (GIF menor).
    q2, d2 = [], []
    for q, d in zip(quadros, duracoes):
        if q2 and q.tobytes() == q2[-1].tobytes():
            d2[-1] += d
        else:
            q2.append(q)
            d2.append(d)
    q2[0].save(caminho, save_all=True, append_images=q2[1:], duration=d2, loop=0, optimize=False)


def _folha_de_quadros(quadros: list[Image.Image], tags: dict, caminho: Path, escala: int = 6) -> None:
    """Todos os quadros ampliados lado a lado, uma linha por animação (para revisão)."""
    margem, lado = 4, TAMANHO * escala
    colunas = max(b - a + 1 for a, b in tags.values())
    colunas = min(colunas, 8)
    linhas = sum(math.ceil((b - a + 1) / colunas) for a, b in tags.values())
    folha = Image.new(
        "RGB", (colunas * (lado + margem) + margem, linhas * (lado + margem) + margem), (90, 90, 110)
    )
    linha = 0
    for a, b in tags.values():
        for k, i in enumerate(range(a, b + 1)):
            x = margem + (k % colunas) * (lado + margem)
            y = margem + (linha + k // colunas) * (lado + margem)
            folha.paste(_ampliar(quadros[i], escala), (x, y))
        linha += math.ceil((b - a + 1) / colunas)
    folha.save(caminho)


def exportar_pet(pet: Pet, saida: Path, escala: int = 8, previews: bool = True) -> Resultado:
    cores = pet.mapa_de_cores()
    quadros: list[Image.Image] = []
    duracoes: list[int] = []
    tags: dict[str, tuple[int, int]] = {}
    pontos: dict[str, dict[str, tuple[int, int]]] = {}

    for nome, poses in animacoes_do_pet(pet).items():
        inicio = len(quadros)
        pontos[nome] = pet.pontos(poses[0])
        for pose in poses:
            quadros.append(renderizar(pet, pose, cores))
            duracoes.append(pose.duracao)
        tags[nome] = (inicio, len(quadros) - 1)

    (saida / "sprites").mkdir(parents=True, exist_ok=True)
    (saida / "preview").mkdir(parents=True, exist_ok=True)

    folha = Image.new("RGBA", (TAMANHO * len(quadros), TAMANHO), (0, 0, 0, 0))
    for i, q in enumerate(quadros):
        folha.paste(q, (i * TAMANHO, 0))
    png = saida / "sprites" / f"{pet.id}.png"
    folha.save(png)

    meta = {
        "frames": [
            {
                "filename": f"{pet.id} {i}",
                "frame": {"x": i * TAMANHO, "y": 0, "w": TAMANHO, "h": TAMANHO},
                "duration": d,
            }
            for i, d in enumerate(duracoes)
        ],
        "meta": {
            "app": "pets/petgen",
            "image": png.name,
            "format": "RGBA8888",
            "size": {"w": folha.width, "h": folha.height},
            "scale": "1",
            "frameTags": [
                {"name": n, "from": a, "to": b, "direction": "forward"} for n, (a, b) in tags.items()
            ],
            # Pontos de referência (1º quadro de cada animação), em pixels do quadro.
            "pontos": pontos,
            # Animações especiais: evento que dispara, animações e fundo de tela.
            "extras": [
                {"id": x["id"], "gatilho": x.get("gatilho"), "fundo": x.get("fundo"),
                 "animacao": f"extra_{x['id']}"}
                for x in pet.config.get("extras", []) if f"extra_{x['id']}" in tags
            ],
        },
    }
    png.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    if not previews:
        return Resultado(pet, png, quadros, duracoes, tags, pontos)
    _folha_de_quadros(quadros, tags, saida / "preview" / f"{pet.id}_quadros.png")
    for nome, (a, b) in tags.items():
        _salvar_gif(
            [_ampliar(q, escala) for q in quadros[a : b + 1]],
            duracoes[a : b + 1],
            saida / "preview" / f"{pet.id}_{nome}.gif",
        )
    return Resultado(pet, png, quadros, duracoes, tags, pontos)


def _quadro_no_tempo(r: Resultado, a: int, b: int, t: int) -> Image.Image:
    total = sum(r.duracoes[a : b + 1])
    t %= total
    for i in range(a, b + 1):
        if t < r.duracoes[i]:
            return r.quadros[i]
        t -= r.duracoes[i]
    return r.quadros[b]


def preview_conjunto(resultados: list[Resultado], saida: Path, escala: int, anim: str = "idle") -> Path:
    """GIF com todos os pets lado a lado na mesma linha do tempo + PNG estático com nomes."""
    tamanhos = [sum(r.duracoes[r.tags[anim][0] : r.tags[anim][1] + 1]) for r in resultados]
    total = math.lcm(*tamanhos)
    if total > 15000:
        total = max(tamanhos) * 2
    passo = 10
    w = TAMANHO * len(resultados)

    quadros, duracoes = [], []
    for t in range(0, total, passo):
        cena = Image.new("RGBA", (w, TAMANHO), (0, 0, 0, 0))
        for i, r in enumerate(resultados):
            a, b = r.tags[anim]
            cena.alpha_composite(_quadro_no_tempo(r, a, b, t), (i * TAMANHO, 0))
        quadros.append(_ampliar(cena, escala))
        duracoes.append(passo)
    gif = saida / "preview" / "todos.gif"
    _salvar_gif(quadros, duracoes, gif)

    # PNG estático com nomes.
    estatico = quadros[0].copy()
    tela = Image.new("RGB", (estatico.width, estatico.height + 40), FUNDO)
    tela.paste(estatico, (0, 0))
    d = ImageDraw.Draw(tela)
    fonte = ImageFont.load_default(size=22)
    for i, r in enumerate(resultados):
        cx = (i * TAMANHO + TAMANHO // 2) * escala
        d.text((cx, estatico.height + 18), r.pet.nome, fill=(240, 236, 228), font=fonte, anchor="mm")
    tela.save(saida / "preview" / "todos.png")
    return gif
