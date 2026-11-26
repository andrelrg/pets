# pets 🐶🐶

Dois mascotes em pixel art 8-bit que avisam sobre progresso de tarefas,
problemas e notificações importantes — com animações e falas. Primeiro rodam
num simulador no PC; depois, numa telinha controlada por um microcontrolador
(ESP32).

Os mascotes de referência são **Simba** e **Nala**, mas o projeto é um motor
genérico: qualquer pessoa pode **criar os próprios pets** descrevendo as
características num arquivo de configuração. A partir dele, os sprites e as
animações são gerados.

<p align="center"><img src="docs/img/preview.gif" alt="Nala e Simba em pixel art, animação idle" width="512"></p>

> Projeto em construção. Veja [`docs/arquitetura.md`](docs/arquitetura.md) e
> [`docs/tecnologias.md`](docs/tecnologias.md).

## Gerando os sprites

```bash
python -m venv .venv
.venv/Scripts/activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m tools.petgen        # ou: python -m tools.petgen simba
```

Saídas em `build/`:

| Arquivo | O que é |
|---|---|
| `sprites/<id>.png` + `.json` | spritesheet 48×48 + metadados no formato do Aseprite (tags = animações) |
| `preview/<id>_<anim>.gif` | preview ampliado de cada animação |
| `preview/<id>_quadros.png` | todos os quadros ampliados, para revisão |
| `preview/todos.gif` | todos os pets lado a lado |

## Criando o seu pet

1. Copie `pets/nala/` para `pets/<seu_pet>/`.
2. Edite o `pet.toml`: porte, orelhas, focinho, olhos, padrão da pelagem,
   cores e personalidade. As variantes disponíveis são os arquivos em
   `art/templates/cachorro/` (ex.: `orelha/semi_caidas.txt` → `orelhas = "semi_caidas"`).
3. Rode `python -m tools.petgen <seu_pet>`.

Faltou uma variante? Os templates são grades de texto (um caractere por pixel,
legenda em `art/templates/cachorro/legenda.toml`). Contribuições são bem-vindas!

## Estrutura

```
pets/<id>/      pacote de cada pet (pet.toml, falas, overrides, extras)
art/templates/  templates base da pixel art (partes em camadas, em texto)
sim/            simulador no PC (Python + pygame-ce)
firmware/       firmware do microcontrolador (PlatformIO + LovyanGFX)
tools/          gerador de sprites a partir do pet.toml + conversores (→ C)
docs/           documentação
build/          saídas geradas (ignorada pelo git)
reference/      fotos de referência — IGNORADA pelo git, nunca é commitada
```

## Licença

[MIT](LICENSE)
