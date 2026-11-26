# Tecnologias

Decisões iniciais. Tudo aqui pode mudar conforme o projeto evolui — a ideia é
começar simples e manter o caminho até o microcontrolador sempre aberto.

## Visão geral do pipeline

```
 Aseprite / LibreSprite         tools/ (Python)              destino
 ┌──────────────────┐   export  ┌──────────────┐   gera   ┌──────────────────────┐
 │ art/*.aseprite   │ ───────▶  │ spritesheet  │ ───────▶ │ sim/  (PC, pygame)   │
 │ (fonte editável) │  PNG+JSON │ → RGB565 .h  │          │ firmware/ (ESP32)    │
 └──────────────────┘           └──────────────┘          └──────────────────────┘
                                                                   ▲
                                 eventos JSON (serial / Wi-Fi) ────┘
                                 {"pet":"a","anim":"alerta","say":"Build quebrou!"}
```

## 1. Arte (8-bit)

| Item | Escolha | Por quê |
|---|---|---|
| Editor | **Aseprite** (ou **LibreSprite**, fork grátis) | Padrão de pixel art; timeline de animação, tags por animação, export de spritesheet + JSON. Alternativa no navegador: Piskel. |
| Fonte da arte | `art/*.aseprite` versionado | Arquivo editável fica no repo, não só o PNG. |
| Export | `assets/sprites/<pet>.png` + `<pet>.json` (formato Aseprite, *array*, com *frame tags*) | Cada tag = uma animação (`idle`, `falando`, `feliz`, `alerta`, `dormindo`...). |
| Tamanho do sprite | **32×32 px** por frame (talvez 48×48 se faltar detalhe) | Lê bem escalado ×4–×7 em telas de 128–240 px. |
| Paleta | Limitada, **16 cores**, criada a partir das cores dos cachorros | Estética 8-bit + cabe fácil em memória (4 bits/pixel). |
| Fonte do texto | Fonte bitmap pixel (ex.: 5×7 ou 8×8) com licença livre | Mesma fonte no simulador e no ESP32. |

## 2. Programa que dispara animações + falas

**Fase 1 — Simulador no PC (`sim/`)**: Python 3.12 + **pygame-ce**.

- Mostra uma "tela virtual" do mesmo tamanho da tela física (ex.: 240×240), escalada na janela.
- Lê os spritesheets do Aseprite e toca as animações pelas tags.
- **Fala**: balão de diálogo com efeito *typewriter* (letra por letra), boca
  animando enquanto o texto aparece, e "bipes" 8-bit por sílaba (estilo voz de
  personagem de jogo retrô) — gerados por síntese simples, sem arquivos de áudio.
- Recebe eventos por uma API mínima: CLI (`pets say ...`), HTTP local, ou
  stdin — assim qualquer coisa (scripts, CI, hooks do git, etc.) consegue
  acionar os mascotes.

**Fase 2 — Hardware (`firmware/`)**:

| Item | Sugestão inicial |
|---|---|
| Placa | **ESP32-S3** (PSRAM, Wi-Fi, USB nativo) — ESP32 comum também serve |
| Tela | TFT **ST7789 240×240** ou **GC9A01 240×240 redonda** (colorida, SPI, barata). OLED SSD1306 128×64 é opção monocromática. |
| Build | **PlatformIO** + framework Arduino |
| Gráficos | **LovyanGFX** (rápido, sprites/DMA, suporta as telas acima) |
| Áudio (opcional) | Buzzer piezo ou I2S (MAX98357A) para os bipes |
| Comunicação | Mesmo protocolo JSON do simulador, via **Serial USB** primeiro, depois **Wi-Fi (HTTP ou MQTT)** |

Os sprites vão para o firmware como arrays C (`RGB565` ou indexados por
paleta) gerados por um script em `tools/` — a arte tem uma única fonte de
verdade.

## 3. Protocolo de eventos (rascunho)

```json
{ "pet": "a", "anim": "alerta", "say": "Os testes falharam!", "prioridade": "alta" }
```

- `pet`: qual dos dois mascotes (ou `"ambos"`).
- `anim`: nome da tag de animação.
- `say`: texto da fala (opcional).
- `prioridade`: `baixa` | `normal` | `alta` — define se interrompe a fala atual.

## 4. Privacidade

Fotos dos cachorros ficam em `reference/`, que é ignorada pelo git. Só a arte
pixelada derivada (e nada pessoal) entra no repositório.
