# 03 · Arquitetura Proposta (ainda não implementada)

Estrutura de repositório planejada para quando começarmos a fase de código. Nada disto existe ainda. Atualizado após confirmar o contrato técnico real em `01-definicao-problema.md`.

```
pokemon_challenge/
├── docs/                       # esta pasta: plano, decisões, pesquisa
├── vendor/
│   └── cg/                     # runtime oficial (api.py, sim.py, game.py, utils.py, libcg*.so/dll/dylib)
│                                # ⚠️ NÃO versionado no git — licença proíbe redistribuição (ver 06-riscos-*.md).
│                                # Baixado via scripts/fetch_official.sh, listado no .gitignore.
├── data/
│   ├── cards/                  # cache local de all_card_data()/all_attack() (derivado da lib, não do CSV redistribuído)
│   └── decks/                  # decks candidatos em .csv próprio (1 Card ID por linha, 60 linhas)
├── agent/
│   ├── main.py                 # entry point da submissão: agent(obs_dict) -> list[int]
│   ├── policy_baseline.py      # Fase 1: sempre escolhe a 1ª opção legal / regra fixa
│   ├── policy_heuristic.py     # Fase 2: scoring de cada Option em obs.select.option
│   ├── policy_search.py        # Fase 3: usa search_begin/search_step (API nativa) para MCTS com determinização
│   └── fallback.py             # garante índice válido dentro de [minCount, maxCount], sem duplicatas
├── eval/
│   ├── local_match.py          # battle_start/battle_select do cg/game.py — N partidas política A vs B
│   ├── matchup_matrix.py       # matriz de winrate entre decks candidatos
│   └── reports/                # saídas de avaliação (não versionar dados brutos grandes)
├── build/
│   └── package_submission.sh   # empacota main.py + deck.csv + vendor/cg/ em submission.tar.gz
├── scripts/
│   └── fetch_official.sh       # baixa/atualiza vendor/cg/ e dados oficiais via `kaggle competitions download`
├── research/                   # notas de meta, experimentos descartados
└── README.md
```

## Decisões de design (a manter conforme o projeto evolui)

- **`vendor/cg/` nunca é commitado.** A licença (`LicenseRef-PTCG-ABC-Competition-Use-Only`) proíbe redistribuição do engine e dos dados de carta em PDF/CSV oficiais. `.gitignore` cobre `vendor/`, `*.dll`, `libcg*`, os PDFs/CSVs baixados brutos. `scripts/fetch_official.sh` recria essa pasta a partir da API do Kaggle sempre que necessário.
- **Política separada de deck**: `agent/policy_*.py` deve funcionar com qualquer deck de 60 cartas compatível; o deck ativo é um dado (`data/decks/*.csv`), não hardcoded.
- **Um único ponto de fallback**: toda política passa pela mesma checagem centralizada em `agent/fallback.py` antes de retornar — índice dentro de `[minCount, maxCount]`, dentro de `range(len(option))`, sem duplicatas. Isso é literalmente o contrato de `search_step`/`Select` do engine (erros 4, 5, 6 documentados em `cg/api.py`), então dá pra validar localmente antes de qualquer submissão.
- **`eval/` roda 100% localmente** via `cg/game.py` (`battle_start`/`battle_select`), sem tocar o Kaggle — submissões diárias são limitadas.
- **Busca (Fase 3) usa o motor oficial, não um motor próprio**: `agent/policy_search.py` chama `search_begin`/`search_step` (ver `01-definicao-problema.md`) em vez de reimplementar as regras do PTCG — reduz drasticamente o escopo de "construir um motor de jogo".

## Em aberto

- Confirmar se `search_begin`/`search_step` tem custo de performance compatível com o limite de tempo por jogada em produção (a confirmar no `/rules`) — se for caro, MCTS pode precisar rodar só em fases não críticas de tempo (ex.: durante o turno do oponente, se isso for permitido).
- Definir formato de cache/serialização para `all_card_data()`/`all_attack()` (chamados via `ctypes` toda vez que o processo sobe — vale cachear em JSON local versionado, já que são dados de jogo e não trecho de engine).
