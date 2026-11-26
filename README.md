# pets 🐶🐶

Dois mascotes em pixel art 8-bit que avisam sobre progresso de tarefas,
problemas e notificações importantes — com animações e falas. Primeiro rodam
num simulador no PC; depois, numa telinha controlada por um microcontrolador
(ESP32).

Os mascotes de referência são **Simba** e **Nala**, mas o projeto é um motor
genérico: qualquer pessoa pode **criar os próprios pets** descrevendo as
características num arquivo de configuração. A partir dele, os sprites e as
animações são gerados.

> Projeto em construção. Veja [`docs/arquitetura.md`](docs/arquitetura.md) e
> [`docs/tecnologias.md`](docs/tecnologias.md).

## Estrutura

```
pets/<id>/      pacote de cada pet (pet.toml, falas, overrides, extras)
art/            templates base da pixel art (partes em camadas)
assets/sprites/ spritesheets exportados (PNG + JSON)
sim/            simulador no PC (Python + pygame-ce)
firmware/       firmware do microcontrolador (PlatformIO + LovyanGFX)
tools/          gerador de sprites a partir do pet.toml + conversores (→ C)
docs/           documentação
reference/      fotos de referência — IGNORADA pelo git, nunca é commitada
```

## Licença

[MIT](LICENSE)
