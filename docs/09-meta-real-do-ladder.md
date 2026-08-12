# 09 · Meta real do ladder (dados de outros agentes)

Registrado em 12/08/2026. Até aqui, todo teste de deck (`docs/08-status-implementacao.md`) foi contra adversários que **nós mesmos construímos** (placeholder, Psychic, Fighting, Darkness, Water-evo, Fire) — risco reconhecido de overfitting ao nosso próprio viés de deckbuilding. Esta seção documenta a descoberta de fontes de dados reais do ladder, a extração de decks reais, e o que isso revelou.

## O que existe

1. **`kaggle/pokemon-tcg-ai-battle-episodes-YYYY-MM-DD`** (datasets oficiais, um por dia, licença CC0): replays reais de partidas do ladder. Cada episódio é um JSON individual (~1-7MB, dá pra baixar arquivo a arquivo em vez do dataset inteiro) no formato `kaggle_environments` padrão — `steps[0][0]['visualize'][0]['action']` traz os **decks completos revelados dos dois jogadores** (60 Card IDs cada), diferente da `Observation` real de cada agente (que não vê a mão/deck do oponente). `data/meta/episodes_manifest.csv` lista os dias disponíveis (via `kaggle/pokemon-tcg-ai-battle-episodes-index`, também CC0).
2. **`busyaprime/pokemon-tcg-ai-battle-live-meta`** (comunidade, CC BY 4.0, não oficial): tier list processada, matriz de matchup, recomendador de deck. Salvo em `data/meta/*.csv`.
3. **`scripts/extract_real_decks.py`** (criado nesta sessão): baixa episódios individuais e extrai decklists reais + resultado (vitória/derrota) + assinatura de arquétipo (top-3 Pokémon por contagem). Reprodutível — só apontar pra uma pasta de JSONs de episódios baixados.

## Meta real (snapshot 31/07, comunidade) — 8 arquétipos, quase 100% do campo

| Arquétipo | Uso | Winrate | Expectativa vs. campo |
|---|---|---|---|
| `Marnie's Grimmsnarl ex` | **63.8%** (dominante) | 48.8% | 48.0% |
| `Mega Kangaskhan ex` | 8.4% | 50.9% | 50.8% |
| `Fezandipiti ex` | 7.5% | 48.8% | 47.0% |
| `Mega Lopunny ex` | 5.0% | 64.2% | 62.1% |
| `Team Rocket's Mewtwo ex` | 3.7% | 47.9% | 46.5% |
| `Teal Mask Ogerpon ex` | 3.4% | 60.8% | **69.3%** (melhor) |
| `Cynthia's Garchomp ex` | 3.7% | 55.8% | 54.6% |
| `Dragapult ex` | 2.6% | 59.2% | 56.7% |

## Amostra própria extraída (30 episódios de 10/08, 58 decks, 17 arquétipos distintos)

Confirma a tier list e adiciona granularidade: `Munkidori`/`Marnie's Impidimp`/`Morgrem` (a linha do `Marnie's Grimmsnarl ex`) e `Abra`/`Kadabra`/`Alakazam` empatados como mais comuns (10/58 cada, 40% winrate cada nesta amostra pequena); `Dunsparce`/`Dudunsparce`/`Buneary` com o melhor winrate observado (5/7 = 71%); `Teal Mask Ogerpon ex` aparece em várias variações de tech.

## Teste real: nosso Grass contra decklists reais extraídas (não recriadas por nós)

Salvos em `data/decks/real_*.csv` (decklist do vencedor de cada arquétipo, extraída de verdade — não uma aproximação nossa). Testado com `policy_heuristic` nos dois lados:

| Adversário real | Winrate do Grass |
|---|---|
| `real_munkidori_marnies-impidimp.csv` (linha do Grimmsnarl ex, **63.8% de uso no ladder**) | **100%** (25/25) |
| `real_abra_kadabra.csv` (linha do Alakazam) | **91%** (32/35) |
| `real_dunsparce_dudunsparce.csv` | **68%** (17/25) |
| `real_teal-mask-ogerpon-ex.csv` (melhor expectativa da tier list, 69.3%) | **4%** (1/25) — perdemos feio |

## Por que perdemos contra o Ogerpon (e não contra os outros)

`Teal Mask Ogerpon ex` (`cardId=96`): **210 HP** — mais que o dobro do nosso maior atacante (`Genesect`, 120 HP). Ataque `Myriad Leaf Shower`: "30 dano a mais para cada energia anexada em **ambos** os ativos" — escala com o próprio jogo se alongando, o oposto de um deck de dano fixo como o nosso. Ability `Teal Dance`: uma vez por turno, pode anexar uma **segunda** energia (além da normal) e comprar uma carta ao fazer isso — acelera energia e consistência ao mesmo tempo. É estruturalmente mais forte que qualquer Pokémon não-`ex` do pool: o trade-off que fizemos desde o início (`docs/08`, "Deck escolhido: por quê" — evitar `ex` por dar 2 prêmios ao ser nocauteado) tem um custo real, e `Teal Mask Ogerpon ex` é a prova mais clara disso até agora.

Os outros três arquétipos reais (Marnie's/Munkidori, Alakazam, Dudunsparce) são todos **linhas de evolução de 2-3 estágios** — lentas para montar, e perdem contra um deck de básicos que já ataca com dano relevante desde o turno 2-3, pilotado pela mesma "inteligência" de política simples. Isso é uma validação real e forte da tese "simplicidade vence" que guiou as decisões de deck até aqui — mas só até esbarrar num `ex` de alto HP/escalável, que nenhuma velocidade de ataque básico resolve sozinha.

## Decisão

Não mudei o deck a partir desta descoberta. É informação forte demais para ignorar, mas também grande demais para agir sozinho sem alinhar: incorporar um `ex` tanque como resposta ao Ogerpon é uma mudança de filosofia de deck (não um ajuste), e replicar exatamente esse deck exigiria entender vários trainers que ainda não catalogamos (`Bug Catching Set`, `Pokégear 3.0`, `Harlequin`, `Lively Stadium`, `Tera Orb`, `Jumbo Ice Cream`, `Judge`, `Lillie's Determination`). Também: `Teal Mask Ogerpon ex` tem só 3.4% de uso no ladder — é o melhor pelo `exp_vs_field`, mas o adversário mais provável no ladder de verdade ainda é a linha `Marnie's Grimmsnarl ex` (63.8%), contra a qual vencemos 100% na amostra real. Fica registrado como o próximo ponto de decisão real do projeto, não uma ação já tomada.
