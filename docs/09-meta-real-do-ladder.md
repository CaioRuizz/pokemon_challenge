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

## Atualização: amostra ampliada (199 episódios de 10/08, 398 decks) — o meta girou

A tier list da comunidade é de 31/07 (12 dias antes desta nota). Ampliei a amostra própria de 30 para 199 episódios (398 decks) e agreguei por **presença da carta-chave** (mais robusto que a assinatura "top-3 Pokémon" usada antes, que fragmentava o mesmo arquétipo em várias entradas por causa da ordem de contagem):

| Arquétipo | Uso (amostra de 10/08) | Uso (tier list de 31/07) | Nosso winrate |
|---|---|---|---|
| Linha `Dudunsparce` | **34.4%** | não aparecia no top-8 | 68% (54%¹) |
| Linha `Marnie's Grimmsnarl ex` | 21.9% | 63.8% | 100% (46%¹) |
| Linha `Alakazam` | 17.8% | não aparecia no top-8 | 91% (48%¹) |
| `Teal Mask Ogerpon ex` (todas variantes) | **12.8%** | 3.4% | **4%** (45%¹) |

¹ winrate observado do próprio arquétipo dentro da amostra (contra o campo geral, não contra nós especificamente).

**Conclusão**: o meta mudou substancialmente em 12 dias — `Marnie's Grimmsnarl ex` caiu de dominante (63.8%) para "só" o segundo mais comum (21.9%), e `Teal Mask Ogerpon ex` quadruplicou de uso (3.4% → 12.8%), deixando de ser nicho. Isso muda o cálculo: perder ~96% de 12.8% dos jogos custa uns 12 pontos percentuais de winrate esperado, não os ~3 que eu tinha estimado antes com o dado antigo.

## Tentativa de resposta ao Ogerpon: Tapu Bulu (testada e descartada — achado real, não decisão de política)

`Teal Mask Ogerpon ex` (`cardId=96`) tem 210 HP e escala dano com energia acumulada (ver seção acima). Procurando no pool por um atacante Grass que resolvesse isso, achei **`Tapu Bulu`** (`cardId=920`): HP 140, ataque único `Wood Hammer` — **220 de dano** por 4 energia (2 Grass + 2 Colorless), com único efeito colateral "30 de dano a si mesmo" (não é uma condição que impede o disparo, é sempre aplicável). Isso mataria o Ogerpon (210 HP) num golpe só.

Montei `data/decks/grass_v3.csv` (troca `Shaymin` → `Tapu Bulu`, energia 27→ mantida) e testei contra `real_teal-mask-ogerpon-ex.csv`: **3% de vitória (1/30) — sem nenhuma melhora** (era 4% antes).

**Causa raiz investigada e confirmada por trace**: nossa política **só anexa energia ao Pokémon ativo**, nunca prioriza o banco — mesmo quando o banco tem um atacante muito mais forte parado. Em nenhuma das 30 partidas contra o Ogerpon o `Tapu Bulu` chegou a receber energia suficiente para atacar sequer uma vez (confirmado rastreando `energies` do Tapu Bulu turno a turno). Contra oponentes que demoram mais pra decidir o jogo (ex.: o placeholder, ~13-95 turnos), ele eventualmente entra e ataca (confirmado em 2 de 5 partidas de checagem) — mas contra o Ogerpon, que decide o jogo em ~13-14 turnos, não há tempo.

**Isso é uma limitação de arquitetura real, não uma questão de qual carta escolher**: para qualquer atacante-bomba (custo alto, dano alto) funcionar, a política precisaria rotear energia estrategicamente para o banco quando fizer sentido — exatamente o tipo de mudança (`_score_attach`, "attach direcionado") que **já tentei e revertida** duas seções acima por regredir em todos os matchups testados na época. Não tentei uma terceira variante desse mecanismo agora: o risco de regressão ampla é conhecido e real, e não há tempo nem supervisão disponível hoje para validar com o rigor que essa mudança exige (múltiplos matchups, amostras grandes, sem o usuário disponível para revisar antes de eu consumir a última submissão do dia).

`data/decks/grass_v3.csv` fica no repositório como registro do experimento (não promovido a `agent/deck.csv`).

## Decisão final desta sessão

**Não mudei `agent/deck.csv` nem `agent/policy_heuristic.py`.** Nenhuma mudança tentada hoje (Tapu Bulu) passou na validação. O deck Grass atual (já em produção como v4) continua sendo a melhor versão validada: forte contra o arquétipo mais comum agora (`Dudunsparce`, 34.4%, 68% de winrate) e o antigo dominante (`Grimmsnarl`, 21.9%, 100%), fraco especificamente contra `Ogerpon` (12.8%, 4%). Estimativa de winrate agregado ponderado pelos 4 arquétipos cobertos (86.9% do campo): **~71%** — número saudável mesmo considerando o buraco conhecido do Ogerpon.

**Não fiz uma nova submissão nesta sessão.** O código do agente não mudou desde a v4 (já `COMPLETE` no ladder), então reenviar o mesmo conteúdo não geraria nenhuma informação nova e gastaria desnecessariamente a última submissão disponível hoje — o oposto do que foi pedido ("cuidado para não desperdiçar envios com mudanças rasas"). A v4 continua sendo a submissão vigente.

**Recomendação clara para a próxima sessão** (nesta ordem de prioridade):
1. Implementar roteamento de energia para o banco (`_score_attach`) de forma mais restrita que as tentativas anteriores — só desviar quando o banco tiver um atacante cujo melhor ataque supere em muito (ex.: 1.5×+) o do ativo já pronto — e validar com rigor (todos os arquétipos reais catalogados aqui, amostras de 30+ partidas cada) antes de prometer qualquer ganho.
2. Se isso destravar `Tapu Bulu` (ou similar) como resposta viável, reavaliar o matchup contra `Ogerpon` com o deck `grass_v3.csv` já pronto no repositório.
3. Repetir a extração de decks reais (`scripts/extract_real_decks.py`) contra um dia mais recente antes de decidir qualquer coisa — o meta claramente não é estático (mudou muito em 12 dias), então essa checagem deveria ser rotina, não evento único.
