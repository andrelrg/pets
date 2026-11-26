# Arquitetura — motor genérico + pets configuráveis

O projeto se divide em duas camadas:

1. **Motor** (comum a todos): o simulador, o firmware, o protocolo de eventos,
   o sistema de falas e a lista de animações que todo pet precisa ter.
2. **Pets** (de cada pessoa): a aparência, a personalidade, as falas e as
   animações especiais. Ficam num pacote de configuração.

Simba e Nala são os primeiros pets e servem de exemplo de referência. Qualquer
pessoa pode criar os seus sem mexer no motor.

## Pacote de pet

```
pets/
  simba/
    pet.toml          # características: porte, pelagem, orelhas, olhos, personalidade
    falas.toml        # frases por evento, no tom do pet (opcional, há padrões)
    overrides/        # (opcional) sprites desenhados à mão que substituem os gerados
  nala/
    ...
```

Exemplo de `pet.toml` (rascunho):

```toml
[pet]
id = "nala"
nome = "Nala"
especie = "cachorro"

[aparencia]
porte = 1.0                 # escala relativa (Simba ≈ 0.82)
orelhas = "em_pe"           # em_pe | semi_caidas | caidas
orelha_marca = "corte_ponta_esquerda"
focinho = "longo"
padrao = "tricolor_sela"    # define onde cada cor de pelagem aparece
patas = "brancas"

[aparencia.cores]
base    = "#2b2422"         # pelagem principal
marca   = "#c08a4e"         # manchas / máscara
claro   = "#f2ede4"         # peito, patas
nariz   = "#1e1a19"
olhos   = "#6b3f1f"

[personalidade]
tracos = ["tranquila", "carente"]
energia = 0.3               # 0 = calma, 1 = elétrica — afeta velocidade do idle
desconfianca = 0.1          # afeta pálpebras / olhar lateral
papel = "progresso"         # alerta | progresso | ambos

[voz]
tom = 0.8                   # altura dos bipes de fala
velocidade = 0.9

[[extras]]                  # animação especial (opcional, pode haver várias)
id = "van_nala"
gatilho = "marco"           # evento que dispara essa animação
estilo = "retrato"          # flutuando | retrato
acessorio = "capacete"      # (opcional) template em acessorio/, desenhado sobre a cabeça
fundo = "noite_estrelada"   # espaco | noite_estrelada (desenhados pelo simulador)
```

## Etapa de configuração/geração

```
pet.toml ──▶ gerador (tools/) ──▶ spritesheet PNG + JSON ──▶ simulador / firmware
                 ▲
   templates base (partes em camadas, cores por "papel")
                 ▲
   overrides/ desenhados à mão (opcional, têm prioridade)
```

O gerador monta o pet a partir de **templates em camadas**: corpo, cabeça,
orelhas, olhos, boca, rabo e acessório. Cada parte tem variantes (por exemplo,
orelhas `em_pe`, `semi_caidas` ou `caidas`) e é desenhada com **cores de papel**
(base, marca, claro, sombra, nariz...). Na geração, essas cores são trocadas
pela paleta do pet, uma técnica clássica de 8-bit chamada *palette swap*.

As **animações base são definidas uma vez no template** (posição e quadro de
cada parte ao longo do tempo). Com isso, todo pet novo já nasce com o conjunto
completo de animações. A personalidade ajusta parâmetros como velocidade, a
frequência de piscar, o olhar desconfiado e o quanto o rabo abana.

Quem quiser mais fidelidade desenha quadros à mão em `overrides/`, e eles
substituem os gerados.

## Contrato de animações (todo pet precisa ter)

| Animação | Quando |
|---|---|
| `idle` | Estado padrão |
| `falando` | Durante uma fala (boca animada) |
| `alerta` | Reação a erro / aviso / pendência / deploy |
| `feliz` | Reação a sucesso / marco |
| `pensando` | Reação a progresso; fundo do pet de progresso enquanto há tarefa ativa |
| `curioso` | Reação a info; outros pets olham quando alguém dá alerta |
| `dormindo` | Ocioso por muito tempo (sem eventos) |

As integrações (scripts, CI, hooks) só usam nomes de **eventos**. O motor
traduz cada evento na animação certa de cada pet, então qualquer pet funciona
com qualquer integração.

### Animações especiais (`[[extras]]`)

Cada extra gera três animações: `extra_<id>` (entrada e reação),
`extra_<id>_falando` e `extra_<id>_loop` (depois da fala). Quando chega um
evento igual ao `gatilho`, elas substituem a reação e a fala normais. O fundo
da tela vira o `fundo` do extra e só aquele pet fica em cena, centralizado.
O JSON exportado lista os extras em `meta.extras`.

| Estilo | O que faz |
|---|---|
| `flutuando` | O acessório desce na cabeça e o pet flutua (gravidade zero) |
| `retrato` | Pose de três quartos, altiva, como num quadro |

| Fundo | O que mostra |
|---|---|
| `espaco` | Estrelas cintilando, planeta com anel, estrela cadente e a Terra |
| `noite_estrelada` | Céu em redemoinhos, lua, cipreste, colinas e moldura dourada |

## Cenas (vários pets)

Uma **cena** é uma coreografia entre pets numa linha do tempo: cada passo diz
qual animação um pet toca, por quanto tempo e para onde ele se desloca na tela.
Os papéis são escolhidos pela personalidade, então a cena funciona com
qualquer par de pets.

- **carinho** (enquanto todos dormem): o pet com mais `energia` acorda, vai aos
  pulinhos até o de mais `carinho`, fica em pé atrás dele e lambe a ponta da
  orelha (o outro fica `deitado_feliz`, com corações), depois volta e dorme.
  O alvo é calculado pelos pontos de referência exportados no JSON (`boca` do
  ativo → `orelha` do passivo).

Qualquer evento interrompe a cena.

## Eventos → animação + fala

```json
{ "evento": "erro", "detalhe": "3 testes falharam", "pet": "auto" }
```

- `pet: "auto"` deixa o motor escolher pelo `papel`. Um pet de `alerta` reporta
  erros e um de `progresso` reporta andamento e sucesso.
- A fala sai de `falas.toml` (ou dos padrões), preenchida com o `detalhe`.

## Público × privado

- `pets/<id>/` é público: só traz características e arte pixelada.
- Fotos e anotações pessoais ficam em `reference/` (ignorada pelo git).
