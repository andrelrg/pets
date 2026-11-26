"""Leitura da fonte pixel (art/fontes/*.txt) e composição dos acentos.

Cada glifo vira uma lista de ALTURA linhas ("#"/"."):
    linhas 0-1  espaço para acentos de maiúsculas
    linhas 2-8  altura das maiúsculas (minúsculas ocupam 4-8)
    linhas 9-10 descendentes
Sem dependências: usado pelo simulador e pelos conversores para o firmware.
"""

from __future__ import annotations

from pathlib import Path

ALTURA = 11
TOPO = 2           # linhas reservadas aos acentos das maiúsculas
LARGURA_ESPACO = 3

MARCAS = {
    "agudo": [".#", "#."],
    "grave": ["#.", ".#"],
    "circunflexo": [".#.", "#.#"],
    "til": [".#.#", "#.#."],
    "trema": ["...", "#.#"],
}
ACENTOS = {
    "á": ("a", "agudo"), "à": ("a", "grave"), "â": ("a", "circunflexo"), "ã": ("a", "til"), "ä": ("a", "trema"),
    "é": ("e", "agudo"), "è": ("e", "grave"), "ê": ("e", "circunflexo"), "ë": ("e", "trema"),
    "í": ("i", "agudo"), "ì": ("i", "grave"), "î": ("i", "circunflexo"), "ï": ("i", "trema"),
    "ó": ("o", "agudo"), "ò": ("o", "grave"), "ô": ("o", "circunflexo"), "õ": ("o", "til"), "ö": ("o", "trema"),
    "ú": ("u", "agudo"), "ù": ("u", "grave"), "û": ("u", "circunflexo"), "ü": ("u", "trema"),
    "ñ": ("n", "til"),
}
ACENTOS.update({k.upper(): (v.upper(), m) for k, (v, m) in list(ACENTOS.items())})
SINONIMOS = {"–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'", " ": " "}


def _bloco_vazio(largura: int) -> list[list[str]]:
    return [["."] * largura for _ in range(ALTURA)]


def carregar(caminho: Path) -> dict[str, list[str]]:
    glifos: dict[str, list[str]] = {}
    linhas = [l.rstrip("\n") for l in caminho.read_text(encoding="utf-8").splitlines()]
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if not linha.startswith("> "):
            i += 1
            continue
        chars = linha[2:]
        desenho = [l.split(" ") for l in linhas[i + 1 : i + 10]]
        if len(desenho) != 9 or any(len(d) != len(chars) for d in desenho):
            raise ValueError(f"{caminho}: bloco '{chars}' malformado (linha {i + 1})")
        for k, ch in enumerate(chars):
            colunas = [d[k] for d in desenho]
            if len({len(c) for c in colunas}) != 1:
                raise ValueError(f"{caminho}: glifo '{ch}' com linhas de larguras diferentes")
            glifos[ch] = ["." * len(colunas[0])] * TOPO + colunas
        i += 10

    glifos[" "] = ["." * LARGURA_ESPACO] * ALTURA

    # Acentos compostos sobre a letra-base.
    for ch, (base, marca) in ACENTOS.items():
        if base not in glifos:
            continue
        g = [list(l) for l in glifos[base]]
        w = len(g[0])
        if base == "i":
            g[TOPO][:] = ["."] * w            # i sem pingo
            g[TOPO + 1][:] = ["."] * w
        m = MARCAS[marca]
        mw = len(m[0])
        x0 = (w - mw + 1) // 2
        y0 = 0 if base.isupper() else TOPO
        for j, linha in enumerate(m):
            for k, px in enumerate(linha):
                if px == "#" and 0 <= x0 + k < w:
                    g[y0 + j][x0 + k] = "#"
        glifos[ch] = ["".join(l) for l in g]

    # Cedilha.
    for base, cauda in (("c", [".#..", "#..."]), ("C", ["..#..", ".#..."])):
        if base in glifos:
            g = [list(l) for l in glifos[base]]
            for j, linha in enumerate(cauda):
                g[TOPO + 7 + j] = list(linha[: len(g[0])].ljust(len(g[0]), "."))
            glifos["ç" if base == "c" else "Ç"] = ["".join(l) for l in g]

    for de, para in SINONIMOS.items():
        if para in glifos:
            glifos[de] = glifos[para]
    return glifos
