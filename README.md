# pets 🐶🐶

Dois mascotes em pixel art 8-bit que avisam sobre progresso de tarefas,
problemas e notificações importantes — com animações e falas. Primeiro rodam
num simulador no PC; depois, numa telinha controlada por um microcontrolador
(ESP32).

> Projeto em construção. As decisões de tecnologia estão em
> [`docs/tecnologias.md`](docs/tecnologias.md).

## Estrutura

```
art/            fontes editáveis da pixel art (.aseprite)
assets/sprites/ spritesheets exportados (PNG + JSON)
sim/            simulador no PC (Python + pygame-ce)
firmware/       firmware do microcontrolador (PlatformIO + LovyanGFX)
tools/          scripts de conversão (sprites → C, paleta, etc.)
docs/           documentação
reference/      fotos de referência — IGNORADA pelo git, nunca é commitada
```

## Licença

[MIT](LICENSE)
