"""Animações base, parametrizadas pela personalidade do pet.

Cada função recebe um Pet e devolve uma lista de Poses. Todo pet ganha as
mesmas animações; a personalidade muda o ritmo e os detalhes.
"""

from __future__ import annotations

from .pet import Pet, Pose


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def _ms(valor: float) -> int:
    return int(round(valor / 10) * 10)


def idle(pet: Pet) -> list[Pose]:
    p = pet.personalidade
    energia = p.get("energia", 0.5)
    desconfianca = p.get("desconfianca", 0.3)
    carinho = p.get("carinho", 0.5)

    passo = _ms(_lerp(340, 170, energia))           # respiração: calma = lenta
    olhos = "desconfiado" if desconfianca >= 0.6 else "aberto"
    abana = carinho * (1 - desconfianca) >= 0.3     # tenso = rabo parado
    rabo = ("a", "b") if abana else ("a", "a")
    relaxada = energia < 0.4                         # orelhas descansam às vezes
    lingua = carinho >= 0.7 and desconfianca < 0.5   # feliz e à vontade: língua de fora

    def respira(n: int, **extra) -> list[Pose]:
        base = {"olhos": olhos, "duracao": passo, **extra}
        return [Pose(dy_cabeca=i % 2, rabo=rabo[i % 2], **base) for i in range(n)]

    seq: list[Pose] = []
    seq += respira(4)
    seq += [Pose(olhos="fechado", rabo=rabo[0], duracao=110)]   # piscada
    seq += respira(4)

    if desconfianca >= 0.5:
        # Vigia: olha de canto para um lado, depois para o outro, e se alerta.
        segura = _ms(_lerp(500, 1000, desconfianca))
        seq += [
            Pose(olhos=olhos, olhar=(-1, 0), rabo="a", duracao=segura),
            Pose(olhos=olhos, olhar=(0, 0), rabo="a", duracao=passo),
            Pose(olhos=olhos, olhar=(1, 0), rabo="a", duracao=segura),
            Pose(olhos=olhos, olhar=(0, 0), rabo="a", duracao=passo),
            Pose(olhos="aberto", orelha_esq="alerta", orelha_dir="alerta", rabo="a", duracao=450),
            Pose(olhos="aberto", olhar=(1, 0), orelha_esq="alerta", orelha_dir="alerta", rabo="a", duracao=350),
            Pose(olhos=olhos, orelha_esq="alerta", rabo="a", duracao=280),
        ]
    else:
        # Olhar curioso e tranquilo.
        seq += [
            Pose(olhos=olhos, olhar=(-1, 0), rabo=rabo[0], duracao=passo * 2),
            Pose(olhos=olhos, olhar=(0, 0), rabo=rabo[1], duracao=passo),
        ]
    if lingua:
        seq += respira(6, boca="lingua")
    if relaxada:
        seq += respira(4, orelha_esq="baixa", orelha_dir="baixa")
        seq += [Pose(olhos="meio", orelha_esq="baixa", orelha_dir="baixa", rabo=rabo[0], duracao=700)]

    seq += respira(2)
    return seq


def falando(pet: Pet) -> list[Pose]:
    """Boca abrindo e fechando. O simulador repete enquanto o texto aparece."""
    p = pet.personalidade
    desconfianca = p.get("desconfianca", 0.3)
    velocidade = pet.config.get("voz", {}).get("velocidade", 1.0)
    olhos = "desconfiado" if desconfianca >= 0.6 else "aberto"
    passo = _ms(110 / max(0.3, velocidade))
    seq = []
    for i, boca in enumerate(["aberta", "entreaberta", None, "aberta", None, "entreaberta"]):
        seq.append(Pose(olhos=olhos, boca=boca, dy_cabeca=1 if boca == "aberta" else 0, rabo="a", duracao=passo))
    return seq


def _base_olhos(pet: Pet) -> str:
    return "desconfiado" if pet.personalidade.get("desconfianca", 0.3) >= 0.6 else "aberto"


def alerta(pet: Pet) -> list[Pose]:
    """Pulo de susto, dois latidos e "!" piscando. Desconfiados ainda conferem os lados."""
    p = pet.personalidade
    a = {"orelha_esq": "alerta", "orelha_dir": "alerta", "rabo": "a"}
    seq = [
        Pose(olhos="aberto", dy=-2, boca="aberta", simbolo="exclamacao", duracao=130, **a),
        Pose(olhos="aberto", dy=0, simbolo="exclamacao", duracao=130, **a),
        Pose(olhos="aberto", dy=-1, boca="aberta", simbolo="exclamacao", duracao=120, **a),
        Pose(olhos="aberto", dy=0, simbolo="exclamacao", duracao=220, **a),
        Pose(olhos="aberto", duracao=160, **a),
        Pose(olhos="aberto", simbolo="exclamacao", duracao=260, **a),
    ]
    if p.get("desconfianca", 0.3) >= 0.6:
        seq += [
            Pose(olhos="desconfiado", olhar=(-1, 0), simbolo="exclamacao", duracao=300, **a),
            Pose(olhos="desconfiado", olhar=(1, 0), duracao=300, **a),
        ]
    return seq


def feliz(pet: Pet) -> list[Pose]:
    """Pulinhos com o rabo abanando. Carinhosos mostram coração e língua;
    desconfiados comemoram... e logo voltam a desconfiar."""
    p = pet.personalidade
    carinho, desconfianca = p.get("carinho", 0.5), p.get("desconfianca", 0.3)
    simbolo = "coracao" if carinho >= 0.7 else None
    boca = "lingua" if carinho >= 0.7 else "aberta"
    seq = [
        Pose(olhos="feliz", boca=boca, dy=-(i % 2), rabo="ab"[i % 2], simbolo=simbolo if i >= 2 else None,
             duracao=130)
        for i in range(8)
    ]
    if desconfianca >= 0.6:
        seq += [
            Pose(olhos="aberto", rabo="a", duracao=250),
            Pose(olhos="desconfiado", olhar=(1, 0), rabo="a", duracao=700),
            Pose(olhos="desconfiado", rabo="a", duracao=300),
        ]
    return seq


def pensando(pet: Pet) -> list[Pose]:
    """Olhando para cima com "..." — usado enquanto há tarefa em andamento."""
    p = pet.personalidade
    olhos = _base_olhos(pet)
    olhar = (-1, -1) if olhos == "aberto" else (-1, 0)
    passo = _ms(_lerp(420, 260, p.get("energia", 0.5)))
    seq = []
    for i, pontos in enumerate(["pontos1", "pontos2", "pontos3", None] * 2):
        seq.append(Pose(olhos=olhos, olhar=olhar, dy_cabeca=i % 2, simbolo=pontos, rabo="a", duracao=passo))
    seq.insert(4, Pose(olhos="fechado", olhar=olhar, simbolo="pontos1", rabo="a", duracao=110))
    return seq


def curioso(pet: Pet) -> list[Pose]:
    """Cabeça de lado, uma orelha diferente da outra, "?"."""
    olhos = _base_olhos(pet)
    orelha = "alerta" if pet.config["aparencia"].get("orelhas") == "semi_caidas" else "baixa"
    return [
        Pose(olhos=olhos, dx_cabeca=1, orelha_dir=orelha, olhar=(1, 0), simbolo="interrogacao", duracao=650),
        Pose(olhos="fechado", dx_cabeca=1, orelha_dir=orelha, simbolo="interrogacao", duracao=110),
        Pose(olhos=olhos, dx_cabeca=1, orelha_dir=orelha, olhar=(1, 0), simbolo="interrogacao", duracao=350),
        Pose(olhos=olhos, dx_cabeca=-1, orelha_esq=orelha, olhar=(-1, 0), simbolo="interrogacao", duracao=650),
        Pose(olhos=olhos, dx_cabeca=-1, orelha_esq=orelha, olhar=(-1, 0), duracao=250),
    ]


def dormindo(pet: Pet) -> list[Pose]:
    """Deitado, cabeça sobre as patas, orelhas caídas e Zz subindo."""
    a = {"olhos": "fechado", "orelha_esq": "baixa", "orelha_dir": "baixa", "rabo": None, "postura": "deitado"}
    return [
        Pose(dy_cabeca=0, simbolo="z1", duracao=800, **a),
        Pose(dy_cabeca=1, simbolo="z2", duracao=800, **a),
        Pose(dy_cabeca=1, simbolo=None, duracao=700, **a),
        Pose(dy_cabeca=0, simbolo=None, duracao=700, **a),
    ]


def _acordando(pet: Pet, lado: int) -> list[Pose]:
    """Ainda deitado: abre os olhos, pisca e olha para o lado (lado -1 = esquerda)."""
    a = {"orelha_esq": "baixa", "orelha_dir": "baixa", "rabo": None, "postura": "deitado"}
    return [
        Pose(olhos="fechado", duracao=300, **a),
        Pose(olhos="meio", duracao=300, **a),
        Pose(olhos="fechado", duracao=120, **a),
        Pose(olhos="aberto", duracao=250, **{**a, "orelha_esq": "normal", "orelha_dir": "normal"}),
        Pose(olhos="aberto", olhar=(lado, 0), dx_cabeca=lado, duracao=600,
             **{**a, "orelha_esq": "normal", "orelha_dir": "normal"}),
    ]


def andando(pet: Pet) -> list[Pose]:
    """Pulinhos no lugar; o simulador desloca o pet enquanto toca."""
    olhos = "aberto"
    return [
        Pose(olhos=olhos, dy=-2, rabo="a", duracao=110),
        Pose(olhos=olhos, dy=-1, rabo="b", duracao=90),
        Pose(olhos=olhos, dy=0, rabo="a", duracao=110),
        Pose(olhos=olhos, dy=0, rabo="b", duracao=90),
    ]


def _lambendo(pet: Pet, lado: int) -> list[Pose]:
    """Em pé nas patas de trás (apoiado), cabeça inclinada para o lado, lambidas, olhos felizes."""
    seq = []
    for i in range(6):
        seq.append(Pose(olhos="feliz", dx_cabeca=2 * lado, dy_cabeca=i % 2, boca="lingua" if i % 2 == 0 else "aberta",
                        postura="em_pe", rabo="ab"[i % 2], duracao=170))
    return seq


def deitado_feliz(pet: Pet) -> list[Pose]:
    """Deitado, olhos felizes e corações subindo."""
    a = {"olhos": "feliz", "orelha_esq": "baixa", "orelha_dir": "baixa", "rabo": None, "postura": "deitado"}
    return [
        Pose(simbolo="coracao_sobe1", dy_cabeca=0, duracao=260, **a),
        Pose(simbolo="coracao_sobe2", dy_cabeca=0, duracao=260, **a),
        Pose(simbolo="coracao_sobe3", dy_cabeca=1, duracao=260, **a),
        Pose(simbolo=None, dy_cabeca=1, duracao=200, **a),
    ]


ANIMACOES = {
    "idle": idle,
    "falando": falando,
    "alerta": alerta,
    "feliz": feliz,
    "pensando": pensando,
    "curioso": curioso,
    "dormindo": dormindo,
    # Usadas em cenas com mais de um pet (ex.: carinho enquanto dormem).
    "acordando_esq": lambda pet: _acordando(pet, -1),
    "acordando_dir": lambda pet: _acordando(pet, 1),
    "andando": andando,
    "lambendo_esq": lambda pet: _lambendo(pet, -1),
    "lambendo_dir": lambda pet: _lambendo(pet, 1),
    "deitado_feliz": deitado_feliz,
}
