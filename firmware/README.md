# Firmware

Firmware dos pets para ESP32 (PlatformIO + Arduino). Placas e ligações em
[`docs/hardware.md`](../docs/hardware.md).

## Fase 0: só a placa

Ainda sem tela, o firmware já:
- recebe eventos pelo **Wi-Fi**, com a mesma API do simulador: `POST http://pets.local:8765/evento`;
- recebe eventos pela **serial USB**, uma linha JSON por evento;
- mantém a **fila com prioridades** e o roteamento por papel, como o simulador;
- mostra o estado no **LED azul da placa**.

| Estado / evento | LED |
|---|---|
| idle | respiração bem fraquinha |
| pensando (tarefa em andamento) | um *blip* a cada 2 s |
| dormindo (2 min sem eventos) | apagado |
| erro | 3 piscadas rápidas, repetindo |
| aviso / pendente / tarefa parada | 2 piscadas |
| sucesso | respiração forte |
| marco | batimento duplo |
| deploy | contagem regressiva acelerando, depois aceso |
| progresso / info | piscada curta a cada 1,2 s |

Tarefas seguem as mesmas regras do simulador: `valor` 100 ou `sucesso` concluem a
tarefa, e 10 min sem progresso (ou `limite` segundos) geram o alerta `parado`.

O **botão A** (GPIO 32 → GND) pula a fala atual.

## Como gravar

Com o ambiente do projeto (`.venv`), que já traz o PlatformIO:

```bash
cd firmware
../.venv/Scripts/python -m platformio run -t upload      # compila e grava
../.venv/Scripts/python -m platformio device monitor     # serial (115200)
```

A DevKit V1 usa um conversor USB-serial **CP2102** ou **CH340**. Se o Windows
não criar uma porta COM ao conectar, instale o driver do chip, que vem escrito
na placa. Se a gravação não começar, segure o botão **BOOT** quando aparecer
`Connecting...`.

## Primeiro uso: Wi-Fi

1. Sem rede salva, a placa abre a rede **`pets-config`**. Conecte-se a ela pelo celular.
2. O portal abre sozinho (ou acesse `192.168.4.1`). Escolha a sua rede e digite a senha.
3. A serial mostra `conectado: http://pets.local:8765`.

A senha fica só na flash da placa, nunca no código. Para trocar de rede, digite
`wifi-esquecer` na serial.

## Testando

Pelo PC, com o mesmo comando usado para o simulador:

```bash
python -m sim.enviar erro "3 testes falharam" --host pets.local
python -m sim.enviar progresso "migração" --valor 60 --silencioso --host pets.local
curl http://pets.local:8765/                 # status
```

Também dá para definir `PETS_HOST=pets.local` uma vez e omitir o `--host`.

Ou direto na serial (no monitor):

```
{"evento": "deploy", "detalhe": "v1.4", "pet": "simba"}
status
```

Se o `pets.local` não resolver na sua rede, use o IP mostrado na serial.
