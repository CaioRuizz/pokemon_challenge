# 03 · Arquitetura Proposta (ainda não implementada)

Estrutura de repositório planejada para quando começarmos a fase de código. Nada disto existe ainda — é o alvo do próximo passo, após validação da Fase 0.

```
pokemon_challenge/
├── docs/                      # esta pasta: plano, decisões, pesquisa
├── engine/                    # vendored/wrapper do SDK oficial `cabt` (não versionar assets proprietários se a licença não permitir)
├── data/
│   ├── cards/                 # base de cartas (IDs, texto, atributos) usada para deckbuilding
│   └── decks/                 # decks candidatos em CSV (60 IDs cada)
├── agent/
│   ├── main.py                # entry point exigido pela submissão (contrato agent(obs) -> list[int])
│   ├── policy_baseline.py     # Fase 1: regra fixa
│   ├── policy_heuristic.py    # Fase 2: scoring de ações
│   ├── policy_search.py       # Fase 3: MCTS/determinização
│   └── fallback.py            # garantia de "nunca crashar"
├── eval/
│   ├── local_match.py         # roda N partidas locais entre duas políticas via cabt
│   ├── matchup_matrix.py      # matriz de winrate entre decks/arquétipos candidatos
│   └── reports/               # saídas de avaliação (não versionar dados brutos grandes)
├── build/
│   └── package_submission.sh  # empacota main.py + deck.csv + engine/ em submission.tar.gz
├── research/                  # notas de meta, experimentos descartados
└── README.md
```

## Decisões de design (a manter conforme o projeto evolui)

- **Separar política de deck**: a política (`agent/policy_*.py`) deve funcionar com qualquer deck compatível; o deck ativo é um dado (`data/decks/*.csv`) selecionado por config, não hardcoded.
- **Um único ponto de fallback**: toda política passa pela mesma checagem de "ação legal garantida" antes de retornar, centralizada em `agent/fallback.py` — evita reimplementar a rede de segurança em cada política.
- **`eval/` roda 100% localmente** contra o SDK oficial, sem tocar o Kaggle — submissões são caras (cota diária) e devem ser o último passo, não uma ferramenta de iteração.
- **Sem asset proprietário do jogo commitado no git** se a licença do engine/cartas não permitir redistribuição — confirmar isso na Fase 0 antes de dar `git add` em qualquer coisa baixada do Kaggle.

## Em aberto

- Linguagem/dependências exatas ficam definidas depois de ler o SDK oficial (`cabt`) — provável Python, mas confirmar versão mínima e dependências (ex.: `kaggle_environments`).
- Se o engine já expõe uma API de simulação em lote (batch), isso muda o design de `eval/` (paralelizável vs sequencial).
