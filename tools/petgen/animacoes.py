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


ANIMACOES = {
    "idle": idle,
}
