# 09 · Meta real do ladder (dados de outros agentes)

Registrado em 12/08/2026. Até aqui, todo teste de deck (`docs/08-status-implementacao.md`) foi contra adversários que **nós mesmos construímos** (placeholder, Psychic, Fighting, Darkness, Water-evo, Fire) — risco reconhecido de overfitting ao nosso próprio viés de deckbuilding. Esta seção documenta a descoberta de fontes de dados reais do ladder e a decisão sobre como usá-las.

## O que existe

1. **`kaggle/pokemon-tcg-ai-battle-episodes-YYYY-MM-DD`** (datasets oficiais, um por dia, ~750MB cada, licença CC0): replays reais de partidas do ladder, no mesmo formato `Observation`/`logs` documentado em `docs/01-definicao-problema.md`. Um dataset pequeno, `kaggle/pokemon-tcg-ai-battle-episodes-index`, lista todos os dias disponíveis com contagem de episódios e scores (`data/meta/episodes_manifest.csv`, salvo aqui pois é só metadado/índice, CC0).
2. **`busyaprime/pokemon-tcg-ai-battle-live-meta`** (dataset da comunidade, licença CC BY 4.0, não oficial): já vem processado a partir dos episódios oficiais — tier list de arquétipos, matriz de matchup, e um "recomendador de deck" com expectativa de vitória contra o campo. Salvo em `data/meta/*.csv` (arquivos pequenos, só números agregados, não conteúdo de cartas).

## O que os dados mostram (snapshot de 31/07/2026, ~12 dias antes desta nota)

`data/meta/tier_and_usage.csv` e `data/meta/deck_recommender.csv`:

| Arquétipo | Uso no ladder | Winrate | Expectativa vs. campo |
|---|---|---|---|
| `Marnie's Grimmsnarl ex` | **63.8%** (dominante) | 48.8% | 48.0% |
| `Mega Kangaskhan ex` | 8.4% | 50.9% | 50.8% |
| `Fezandipiti ex` | 7.5% | 48.8% | 47.0% |
| `Mega Lopunny ex` | 5.0% | 64.2% | 62.1% |
| `Team Rocket's Mewtwo ex` | 3.7% | 47.9% | 46.5% |
| `Teal Mask Ogerpon ex` | 3.4% | 60.8% | **69.3%** (melhor expectativa) |
| `Cynthia's Garchomp ex` | 3.7% | 55.8% | 54.6% |
| `Dragapult ex` | 2.6% | 59.2% | 56.7% |

`data/meta/matchup_grid_winrate.csv` tem a matriz completa cabeça-a-cabeça entre esses 8 arquétipos.

## Leitura honesta — o que isso muda e o que não muda ainda

- **Nenhum desses arquétipos se parece com qualquer coisa que testamos.** São todos `ex`, nomeados por treinador (`Marnie's`, `Team Rocket's`, `Cynthia's`) — sinal de decks com sinergias de habilidade/evolução bem mais complexas que os nossos mono-básicos. Isso não invalida o trabalho feito (a troca Fighting→Grass já provou ganho real no ladder oficial, `docs/08`), mas confirma que nossos 6 adversários caseiros cobrem só uma fração pequena do espaço real de oponentes.
- **`Marnie's Grimmsnarl ex` domina em uso (63.8%) mas não é o de melhor winrate/expectativa** — é o mais popular/copiado, não necessariamente o mais forte. Copiar o mais usado não é a mesma decisão que copiar o de melhor `exp_vs_field`.
- **Ressalvas que impedem agir sobre isso às cegas**: (1) fonte não oficial (comunidade, não o Kaggle/Pokémon Company diretamente) — confiável mas não fonte primária; (2) dado de um único dia, ~12 dias antes desta nota — o ladder pode ter girado desde então; (3) tamanhos de amostra desiguais entre matchups (algumas células de `matchup_grid_games.csv` têm menos de 10 partidas, intervalo de confiança provavelmente largo); (4) mesmo confirmando que `Teal Mask Ogerpon ex` é objetivamente o melhor arquétipo, **replicá-lo exigiria pesquisar a decklist completa** (não vem nesses CSVs, só o nome do arquétipo) e nossa política heurística atual pode não saber pilotar um deck com sinergias complexas de evolução/ability tão bem quanto um mono-básico simples — o próprio motivo pelo qual escolhemos deck simples desde o início (`docs/08`, seção "Deck escolhido: por quê").

## Decisão

Não fiz nenhuma mudança de deck ou política a partir desta descoberta ainda — isso é uma virada de estratégia grande o suficiente para não decidir sozinho sem alinhar com o usuário. Próximo passo natural, se aprovado: (1) baixar 1 dia de episódios reais (`kaggle/pokemon-tcg-ai-battle-episodes-*`) e extrair decklists reais de `Teal Mask Ogerpon ex` e/ou `Marnie's Grimmsnarl ex` a partir dos replays; (2) testar se nossa política heurística consegue pilotar essas listas decentemente antes de comprometer uma submissão; (3) considerar se vale simular contra esses arquétipos localmente (reconstruindo o deck a partir dos dados reais) em vez de continuar só contra adversários caseiros.
