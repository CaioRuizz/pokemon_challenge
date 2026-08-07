# 01 · Definição do Problema (Contrato Técnico)

> ✅ **Status: confirmado.** Baixado diretamente da competição via Kaggle API em 07/08/2026 (arquivos oficiais de `pokemon-tcg-ai-battle`). Este documento substitui a versão anterior baseada em repositórios de terceiros.

## O engine: `ptcgProgram` ("cabt Engine")

- Escrito em **C++20**, header-only, sem dependências externas — só a stdlib. Fonte completo (`.h`/`Export.cpp`) é fornecido em `ptcg_engine/ptcgProgram 22/`.
- Compilado como biblioteca nativa e distribuído **já compilado** dentro de cada submissão: `cg.dll` (Windows), `libcg.dylib` (macOS), `libcg.so` / `libcg-arm64.so` (Linux).
- Acessado do Python via **`ctypes`** (`cg/sim.py` carrega a lib e declara `restype`/`argtypes` de cada função exportada).
- **Licença**: uso exclusivo para a competição (`LicenseRef-PTCG-ABC-Competition-Use-Only`). Não pode ser redistribuído, publicado ou usado fora da competição, e deve ser apagado ao final dela. **Implicação direta**: não commitar os binários (`cg.dll`, `libcg*.so`, `libcg.dylib`) nem o source C++ (`ptcg_engine/`) neste repositório git — ver `06-riscos-questoes-abertas.md`.

## Estrutura real de uma submissão

Confirmada pelo `sample_submission/` oficial:

```
submission/
├── main.py       # entry point — deve expor agent(obs_dict) -> list[int]
├── deck.csv      # 60 linhas, uma por linha, cada linha é 1 Card ID (int). NÃO é CSV com vírgulas.
└── cg/           # runtime fornecido pela competição, copiado tal qual
    ├── __init__.py   # vazio
    ├── api.py        # dataclasses (Observation, State, ...) + funções de alto nível + API de search/lookahead
    ├── sim.py         # carrega a lib nativa via ctypes, declara assinaturas C
    ├── game.py        # API de baixo nível para rodar batalhas localmente (battle_start/battle_select) — usada para AVALIAÇÃO LOCAL, não faz parte do agente em si
    ├── utils.py        # conversão dict <-> dataclass
    └── cg.dll / libcg.so / libcg-arm64.so / libcg.dylib   # binário nativo do engine (um por plataforma)
```

O `deck.csv` de exemplo tem 60 linhas; nas primeiras aparece uma progressão de evolução (`1158, 721×3, 722×4, 723×4, 1145×4, 1205×2, 1227×4, 1235×4`) seguida de `3` repetido 34 vezes (card ID 3 = "Basic {W} Energy" — Água básica), ou seja, o deck de exemplo é **quase todo energia básica**, claramente não competitivo — serve só de placeholder.

## Contrato do agente

```python
def agent(obs_dict: dict) -> list[int]:
    """
    Cada elemento do retorno deve ser >= 0 e < len(obs.select.option).
    O tamanho da lista deve estar entre obs.select.minCount e obs.select.maxCount
    (inclusive), sem elementos duplicados.
    """
```

- Na **primeira chamada** de cada partida, `obs_dict["select"]` é `None` → o agente deve retornar os **60 Card IDs do deck** (lidos de `deck.csv`).
- Em todas as chamadas seguintes, `obs.select` descreve a decisão pendente (ver `SelectData` abaixo) e o agente retorna **índices** dentro de `obs.select.option`.
- Path de fallback para `deck.csv`: `/kaggle_simulations/agent/deck.csv` — confirma que o runtime da competição é baseado em **Kaggle Simulations** (o mesmo framework usado em competições tipo `kaggle_environments`), rodando cada agente num sandbox com esse mount.

## Modelo de observação (`cg/api.py`, dataclasses reais)

### `Observation`
```python
select: SelectData | None   # None só na 1ª chamada (seleção de deck)
logs: list[Log]             # eventos ocorridos desde a última seleção
current: State | None       # None só na 1ª chamada
search_begin_input: str | None  # usado internamente pela API de busca (ver abaixo)
```

### `State` (estado atual do jogo)
Turno, `yourIndex` (0 ou 1 — qual jogador é você), `firstPlayer`, flags do turno (`supporterPlayed`, `stadiumPlayed`, `energyAttached`, `retreated`), `result` (-1 se não terminou), `stadium`, `looking` (cartas viradas para cima que você está olhando no momento) e `players: list[PlayerState]` (sempre 2 elementos).

### `PlayerState` (por jogador)
`active` (Pokémon ativo, pode ser `None` se virado pra baixo), `bench`, `benchMax`, `deckCount`, `discard`, `prize` (`None` para cartas de prêmio viradas pra baixo — **você não vê as próprias prize cards até virá-las**), `handCount`, `hand` (**`None` para o oponente** — aqui está a informação imperfeita/oculta), e flags de condição especial (`poisoned`, `burned`, `asleep`, `paralyzed`, `confused`).

### `SelectData` (a decisão pendente)
```python
type: SelectType          # MAIN, CARD, ENERGY, SKILL, ATTACK, EVOLVE, COUNT, YES_NO, ...
context: SelectContext    # ~49 valores: MAIN, SWITCH, TO_ACTIVE, DAMAGE_COUNTER, EVOLVES_FROM,
                           # MULLIGAN, COIN_HEAD, IS_FIRST, SETUP_ACTIVE_POKEMON, ... (enum aberto,
                           # "novos elementos podem ser adicionados durante a competição")
minCount: int
maxCount: int              # nunca excede len(option)
option: list[Option]       # as opções concretas — CADA UMA já vem com os campos relevantes
                            # preenchidos (area, index, playerIndex, attackId, cardId, etc.)
deck: list[Card] | None     # só quando a seleção é sobre o próprio deck
contextCard / effect: Card | None
```

**Importante**: o agente nunca precisa "adivinhar" o espaço de ações — a lib já entrega em `option` exatamente as jogadas legais possíveis para a decisão atual (attach energy, retreat, ability, attack, end turn, etc. — ver `OptionType`, 17 variantes). Isso simplifica MUITO a implementação: não é preciso reimplementar as regras do PTCG para gerar movimentos válidos.

## API de busca/lookahead nativa (achado importante, não estava nas fontes de terceiros)

O engine expõe, além do fluxo normal `agent(obs) -> list[int]`, uma **API de simulação interna** para planejamento:

```python
search_begin(agent_observation, your_deck, your_prize, opponent_deck,
             opponent_prize, opponent_hand, opponent_active, manual_coin=False) -> SearchState
search_step(search_id, select: list[int]) -> SearchState
search_end()
search_release(search_id)
```

- Permite ao agente **rodar o próprio motor C++ internamente** para simular "e se eu jogar X?", incluindo **determinização de informação oculta**: você fornece uma hipótese (`your_deck`, `opponent_deck`, `opponent_prize`, `opponent_hand`, `opponent_active` — todas como listas de Card IDs previstos) e o engine simula a partir daí.
- Isso é exatamente o que MCTS com determinização precisa, e é **fornecido pela própria competição** — não precisamos reimplementar o motor de regras para fazer busca. Isso muda a prioridade da Fase 3 do plano (`02-estrategia-solucao.md`): busca via `search_*` deixa de ser "construir um motor próprio" e passa a ser "usar o motor oficial como simulador para MCTS", o que é bem mais barato de implementar.
- `manual_coin`: permite fixar o resultado de coin flips durante a simulação (útil para explorar as duas ramificações determinísticamente em vez de Monte Carlo puro nesse ponto específico).

## API de avaliação local (`cg/game.py`)

Além da API de submissão, o pacote inclui uma API **separada** para rodar batalhas completas localmente (não faz parte do agente, é ferramenta de dev):

```python
battle_start(deck0: list[int], deck1: list[int]) -> (obs_dict, StartData)
battle_select(select_list: list[int]) -> obs_dict   # aplica uma escolha e retorna a próxima observação
battle_finish()
visualize_data() -> str   # dados para um visualizador externo (útil pra debugar visualmente uma partida)
```

Isso é a base natural do harness de avaliação local descrito em `05-plano-avaliacao.md` — dá pra rodar N partidas entre duas versões do agente sem gastar submissões no Kaggle.

## Base de cartas (`EN Card Data.csv` / `JP Card Data.csv`)

2.103 cartas (2104 linhas incluindo header). Colunas: `Card ID, Card Name, Expansion, Collection No., Stage/Type, Rule, Category, Previous stage, HP, Type, Weakness, Resistance, Retreat, Move Name, Cost, Damage, Effect Explanation`. Também há `all_card_data()` e `all_attack()` em `cg/api.py`, que retornam essa mesma informação estruturada (`CardData`, `Attack` dataclasses) direto da lib nativa — **essa é a fonte de verdade a usar em código**, o CSV é mais para leitura humana/pesquisa de deck.

Campos úteis de `CardData` para deckbuilding: `basic`/`stage1`/`stage2` (linha evolutiva), `ex`/`megaEx` (dá 2 ou 3 prêmios ao oponente quando nocauteado), `tera` (imune a dano enquanto no banco), `aceSpec` (máx. 1 por deck), `weakness`/`resistance`, `retreatCost`, `attacks` (IDs de ataque).

## O que ainda falta confirmar

1. **Regras oficiais completas** (`/rules` da competição) — não lidas ainda, contêm os termos vinculantes e possivelmente detalhes de scoring/ladder que os arquivos de dados não cobrem.
2. **Formato de scoring do ladder** (Elo puro vs TrueSkill μ/σ) — não está nos arquivos baixados; precisa vir da aba Rules/Overview ou de discussão oficial.
3. **Limite de tempo por jogada** — mencionado como existente por fontes de terceiros, mas não visto explicitamente nos arquivos técnicos baixados até agora; confirmar no `/rules`.
4. **Regras de deck legal** (banlist, limite de cópias por carta, formato Standard exato) — os arquivos têm os dados das cartas, mas as regras de construção (ex.: "só 1 ACE SPEC", já visível no dataclass) precisam ser cruzadas com o `/rules` oficial para a lista completa.
