# 11 · Loop contínuo de melhoria (a partir de 12/08/2026)

## Mandato

A partir de 12/08, o usuário pediu para eu continuar em **loop autônomo e auto-pautado**, sem precisar de novos prompts: seguir investigando/melhorando deck, política e robustez; decidir sozinho quando submeter no Kaggle (balanceando ganho validado, risco, cota diária de 5 submissões, e principalmente o horário/prazo restante); e só parar quando a competição Simulation fechar (**16/08/2026 23:59 UTC**) ou o usuário pedir para parar. Este documento registra as iterações desse loop (uma seção por iteração relevante), seguindo a convenção do `CLAUDE.md` de documentar toda mudança e experimento — inclusive os que não funcionaram.

Estado no início do loop: deck `grass_v5.csv` (Celebi→Virizion) em produção, winrate ponderado local de **68.2%** contra os 9 arquétipos reais catalogados em `data/decks/`, submetido como **v7**. Critérios de "satisfatório" (`docs/10`) ainda não batidos: winrate ponderado <80%, e as famílias Ogerpon (~11.8% de uso) e Kangaskhan/Dwebble/Crustle (~10.1%) seguem abaixo de 30% de winrate. Ver `docs/09` e `docs/10` para o histórico completo até aqui.

## Iteração 1 (12/08) — tech Fighting anti-Kangaskhan: negativo, mas revela e corrige bug real na política

**Hipótese**: `Mega Kangaskhan ex` (300 HP, fraco a Fighting) é a peça que trava o matchup `dwebble_crustle_kangaskhan` (23% de winrate no baseline v5). Um atacante Fighting não-`ex` do próprio pool poderia explorar essa fraqueza (2x dano). Melhor candidato encontrado: `Throh` (id 531, 130 HP, 120 dano por só 2 energia — 1 Fighting + 1 incolor, custo de retirada 2).

**Deck testado** (`grass_v9_kangaskhan_tech.csv`, não promovido/removido depois): `grass_v5.csv` com `Pinsir`×4 → `Throh`×4 e 4 `Basic Grass Energy` → 4 `Basic Fighting Energy` (23 grass + 4 fighting).

**Primeira rodada (política sem ajuste), 35 partidas cada arquétipo**: regressão generalizada, e o próprio matchup-alvo piorou (Kangaskhan: 23%→**6%**). Investigando a causa, encontrei um bug real: `_score_attach` (política) nunca olhava **qual carta de energia da mão** estava sendo anexada (`opt["index"]`), só o alvo em campo. Confirmado observando o jogo real que o `ATTACH` expõe uma opção por carta de energia distinta na mão — com energia mono-tipo isso nunca importou, mas com dois tipos em mão a política estava anexando o tipo errado (ex.: Fighting num atacante Grass, ou Grass no `Throh`) sem nenhum critério, na prática ao acaso.

**Correção aplicada** (`agent/policy_heuristic.py`, `_energy_type_match_bonus` + integração em `_score_attach`): prefere a carta de energia da mão cujo tipo bate com o tipo do Pokémon-alvo (ou é `RAINBOW`, que serve para qualquer custo); penaliza levemente o tipo errado. Verificado que é **matematicamente neutro** para um deck mono-tipo (o bônus vira uma constante somada a todas as opções de `ATTACH`, não muda a ordem relativa) — ou seja, correção de baixo risco para a produção atual (`grass_v5`, mono-Grass).

**Segunda rodada (com a correção), 35 partidas**: Kangaskhan voltou a 23% (igual ao v5 sem o tech) — nem melhora nem piora clara. **Achado metodológico importante**: repetindo a MESMA configuração v5-vs-Kangaskhan duas vezes a n=60, os resultados foram **28% e 18%** — uma variação de 10 pontos percentuais só de ruído amostral, mesmo em n=60 (maior que o "padrão" de 30-35 partidas usado nas rodadas anteriores desta sessão). Repetindo o teste do `Throh` a n=60: **20%** — dentro da mesma faixa de ruído do v5 puro (18-28%), ou seja, **estatisticamente indistinguível**, não uma melhora real.

**Conclusão**: o tech de Fighting não resolve o matchup Kangaskhan — mesmo com a energia sendo roteada corretamente, `Throh` tem o mesmo problema estrutural de tudo mais no deck (HP baixo demais para sobreviver ao golpe de 200 de dano do Kangaskhan; e mesmo com 2x de fraqueza, 120×2=240 não mata os 300 HP dele num golpe só). Não promovido, arquivo removido. **Correção do bug de roteamento de energia por tipo, porém, foi mantida** — é estruturalmente correta, neutra na produção atual, e é pré-requisito para qualquer tentativa futura de deck multi-tipo (sem ela, nenhuma tentativa desse tipo pode funcionar, independente de qual carta se escolha).

**Lição metodológica que fica valendo daqui pra frente**: para matchups **fechados/marginais** (perto de empate teórico ou com poucas partidas terminando de forma lopsided), 30-35 partidas não é mais suficiente para decidir com confiança — usar **60 partidas** como padrão em comparações que vão decidir uma promoção, especialmente para o matchup Kangaskhan especificamente, que parece ser inerentemente mais ruidoso que os outros (jogos mais curtos, ~19-23 turnos, com um Pokémon de 300 HP que nocauteia em 1 golpe — o resultado depende muito de quem consegue montar o ataque primeiro, um fator com bastante variância).

**Sem mudança em produção nesta iteração** (o `agent/deck.csv` continua `grass_v5`; a correção de `_score_attach` é um no-op comportamental para esse deck mono-tipo) — nenhuma submissão nova necessária.

## Iteração 2 (12/08) — terceira tentativa de retreat preditivo: inconclusiva, revertida

Investiguei a API `search_begin`/`search_step` (assinatura completa em `vendor/cg/api.py:517-639`): é um simulador determinizado — recebe previsões da informação oculta do oponente (mão, deck, ativo se virado pra baixo) e deixa jogar hipoteticamente com o mesmo mecanismo de `select`/`option` do jogo real, nativo e rápido.Útil para lookahead de verdade, mas antes de investir nisso resolvi tentar mais uma vez, de forma ainda mais restrita, a ideia do "retreat preditivo" que já falhou 2x (`docs/08`) — porque a informação necessária para o caso específico do Kangaskhan (o ativo do oponente já visível no tabuleiro, com energia já anexada visível) **não precisa de previsão nenhuma**, já está 100% em `obs["current"]["players"]`.

**Implementação** (`_best_ready_damage` + `ctx.predictive_danger` em `agent/policy_heuristic.py`, não commitada — revertida ao final): foge do ativo **somente** quando (a) o ataque do oponente já é pagável **agora**, com a energia já anexada (não hipotética) e (b) nosso ativo **não consegue** vencer a troca (matar de volta) neste mesmo turno. Mais restrita que as duas tentativas anteriores, que tratavam qualquer dano teoricamente possível como perigo.

**Resultado**: testado contra o matchup-alvo (Kangaskhan) em dois pares a n=60: 10%→15% (melhora) numa rodada, depois 17%→9% (piora) num sweep completo de 35 partidas contra os 9 arquétipos. Ponderado geral: 58.9% (antes) vs 59.4% (depois) — estatisticamente indistinguível dado o nível de ruído já mapeado no matchup Kangaskhan (swings de 10-18 pontos percentuais entre execuções idênticas, mesmo a n=60). **Nenhuma melhora clara em nenhum lugar, nenhuma regressão clara em nenhum lugar** — um empate estatístico, não um ganho comprovado.

**Decisão**: revertido (`git checkout -- agent/policy_heuristic.py`), terceiro resultado negativo/inconclusivo na mesma linha de investigação. **Conclusão prática**: esgotei a via de heurística reativa/preditiva simples para esse problema — três tentativas com formulações diferentes (ampla, moderada, restrita) não produziram ganho comprovado. O próximo passo real é a API de busca (`search_begin`/`search_step`), não mais variações desse mesmo tipo de regra estática. Fica registrado como não tentar uma quarta vez sem mudar de técnica.

**Achado metodológico adicional**: o matchup Kangaskhan é consistentemente o mais ruidoso de todos os catalogados — mesmo a n=60 (o dobro do padrão usado no resto do projeto), duas execuções idênticas deram 10% e 15%. Registrando isso para não interpretar qualquer resultado futuro isolado desse matchup específico como sinal confiável sem replicação.

## Iteração 3 (12/08) — protótipo de `search_begin`/`search_step`: viabilidade técnica confirmada

**Nota operacional**: o mecanismo de agendamento automático entre iterações (`ScheduleWakeup`) falhou silenciosamente — o container foi reciclado por inatividade antes do despertar disparar (agendado para 04:42 UTC, só percebido às 10:03 UTC quando o usuário perguntou por que o loop tinha parado). Tentativa de trocar por um trigger agendado no servidor (`create_trigger`, mais robusto a reciclagem de container) falhou por permissão bloqueada neste ambiente, mesmo após confirmação do usuário. **Decisão** (a pedido do usuário): sem agendamento automático por ora — o usuário chama para continuar cada iteração (ex.: "continue"), em vez de loop 100% autônomo entre sessões. Registrado para não repetir a suposição de que `ScheduleWakeup` sobrevive a janelas de horas.

**Protótipo**: escrevi dois scripts de teste (`/tmp/.../scratchpad/search_proto.py`, `search_proto2.py`, não commitados — só scratch) chamando `search_begin`/`search_step`/`search_release`/`search_end` a partir de uma partida local real (`grass_v5` vs `real_dwebble_crustle_kangaskhan`), usando uma predição propositalmente ingênua (carta única repetida) para mão/deck do oponente — só para validar a mecânica, não a qualidade da predição.

**Resultado**: funciona de ponta a ponta. `search_begin` sozinho: ~2ms. Uma sequência de 10 passos simulados dentro da busca (`search_step` encadeado): **1.51ms no total** (~0.15ms por passo simulado). **Conclusão**: o custo computacional de rodar buscas de múltiplos turnos, mesmo repetidamente a cada jogada real, é desprezível frente a qualquer limite de tempo plausível (a própria heurística reativa atual já usa ~1-38ms por jogada, então dezenas de rollouts de busca cabem tranquilamente no mesmo orçamento).

**O que falta para um lookahead de verdade (não feito nesta iteração, fica como plano concreto para a próxima)**:
1. **Predição da informação oculta do oponente** (`opponent_hand`, `opponent_deck`) — é o problema difícil de verdade, não a mecânica da API. Abordagem inicial proposta: amostrar as cartas ocultas a partir da distribuição de cartas do oponente já *reveladas* durante a própria partida (jogadas, descarte, prêmios revelados em knockout) em vez de uma carta fixa — melhor que nada, mas ainda imprecisa cedo na partida (pouca informação revelada ainda).
2. **Função de avaliação** do estado simulado resultante (ex.: "nosso ativo sobrevive?", "diferencial de prêmios/energia investida") para comparar linhas de jogada alternativas.
3. **Ponto de integração**: o candidato mais direto continua sendo a decisão de RETREAT (o problema que já falhou 3x com heurística estática — ver iteração 2 acima) — mas agora simulando de fato o próximo turno do oponente (incluindo o que ele *ainda pode jogar da mão*, não só a energia já anexada), que é exatamente a informação que faltava nas 3 tentativas estáticas.
4. Cuidado de engenharia: `search_release`/`search_end` precisam ser chamados de forma confiável mesmo em caminhos de exceção (o protótipo não testou isso sob carga/erro) para não vazar memória nativa numa partida real de dezenas de turnos com múltiplas chamadas por turno.

**Sem mudança em produção nesta iteração** (só protótipo em scratch, nada commitado no agente).

## Iteração 4 (12/08) — tentativa de implementação do lookahead: bloqueada por comportamento não compreendido do `search_step`

Implementei `agent/search_lookahead.py` (commitado, **mas NÃO integrado** em `policy_heuristic.py`/`main.py` — sem nenhum efeito na produção): `active_survives_next_turn(obs, choose_fn, rollouts)` prevê a mão/baralho oculto do oponente por reamostragem das cartas dele já reveladas na partida (descarte + board + energias/ferramentas anexadas), roda `search_begin` e encadeia `search_step` usando a própria `choose_fn` (nossa política real) como proxy de jogada para os dois lados dentro da busca, até sair da janela do turno atual+próximo ou bater um limite de segurança de passos (`_MAX_SIM_STEPS=80`).

**Teste de viabilidade mecânica** (partida real, `grass_v5` vs `real_dwebble_crustle_kangaskhan`, ver iteração 3): funciona sem erro, ~85ms para 3 rollouts completos (~28ms/rollout) — dentro de qualquer orçamento de tempo plausível.

**Problema real encontrado ao rodar em profundidade** (mesma partida, turnos mais avançados, script de debug em `/tmp/.../scratchpad/debug_lookahead.py`): em pelo menos duas execuções, a simulação ficou **presa dentro do próprio turno atual por 75+ passos consecutivos sem o turno avançar** — em um caso repetindo a mesma decisão de ATAQUE (Giga Drain, dano real de 30, não é o bug do ataque-zero já conhecido) sem que o turno mudasse; em outro, ficou presa numa cadeia de **80 seleções forçadas de 1 opção só** (`n_opts=1`), também sem o turno avançar. O limite de segurança (`_MAX_SIM_STEPS`) evitou o travamento infinito de verdade, mas o rollout simplesmente não termina dentro de um orçamento razoável de passos — o resultado da simulação nesses casos não é confiável (nem "seguro" nem "perigoso" de verdade, é só o limite de passos batendo).

**Hipóteses não confirmadas para a causa raiz** (não investigadas a fundo — ficaria para uma sessão dedicada): (a) alguma cadeia de seleção do próprio engine (ex.: resolver um efeito de "procure no baralho") naturalmente precisa de muito mais que 80 sub-seleções quando o baralho previsto é grande, e não é de fato um loop, só um efeito modelado como muitos passos discretos; (b) a predição de mão/baralho do oponente (reamostragem ingênua) pode gerar uma composição "impossível"/degenerada que confunde a lógica do engine ou da nossa própria política de um jeito que não acontece com um baralho real; (c) `search_step` pode ter uma semântica diferente de `battle_select` que não estou respeitando corretamente (não documentada além dos comentários dos dataclasses em `vendor/cg/api.py`).

**Decisão**: não integrar este código à produção enquanto a causa não for entendida — o risco é exatamente o tipo de falha que gerou o `SubmissionStatus.ERROR` da nossa primeira submissão (travamento/timeout numa partida real). O arquivo fica no repositório como ponto de partida documentado para retomar, não como algo pronto para uso. **Dado o custo de investigação já alto e o tempo restante até o prazo (16/08)**, decidi despriorizar esta linha de trabalho pelo resto desta rodada do loop e redirecionar esforço para melhorias de menor risco (mais dados/deck, checagem do score real, robustez) — a busca nativa continua sendo o caminho estruturalmente correto, mas exige uma sessão dedicada a depurar `search_step` isoladamente (com cenários sintéticos pequenos, não uma partida real inteira) antes de valer a pena tentar de novo.

## Iteração 5 (12/08) — nova evidência sobre o bug do `search_step`: reforça a hipótese da predição degenerada

Investiguei mais a fundo o travamento da iteração 4 (script `/tmp/.../scratchpad/debug_lookahead3.py`, log completo salvo em `tool-results/bedhflw32.txt` da sessão). Nos 40 passos logados, **toda** seleção era `type=MAIN, min=1, max=1`, com **exatamente 1 opção disponível: ATACAR** (o mesmo ataque, "Giga Drain" — cura o tanto de dano que causa) — escolhida repetidamente sem o turno avançar nem uma única vez. Isso descarta a hipótese de "efeito legítimo com muitos sub-passos" (não havia nada para escolher além de atacar) e aponta para algo mais específico: como a predição de mão/baralho do oponente é uma reamostragem ingênua das poucas cartas já reveladas (às vezes só 5-15 IDs distintos), o baralho previsto pode ter dezenas de cópias da mesma carta — uma composição **ilegal** (o jogo de verdade limita a 4 cópias) e possivelmente degenerada o bastante para confundir alguma lógica do engine que não foi feita para lidar com isso (ex.: um efeito que resolve "enquanto X for verdade" e nunca deixa de ser verdade porque o baralho fake é anormalmente homogêneo).

**Decisão**: não vale mais investir tempo nisso nesta rodada do loop. O consumo de tempo já foi alto (2 iterações) sem resolução, e mexer na predição para respeitar o limite de 4 cópias é um trabalho não-trivial por si só, que ainda não garantiria eliminar o problema. **Via de busca nativa fica pausada** — arquivo `agent/search_lookahead.py` permanece no repositório como ponto de partida (não integrado, não usado em produção), mas não vou continuar depurando isso nas próximas iterações a menos que surja uma forma de testar em isolamento (baralhos sintéticos pequenos e 100% conhecidos, sem predição nenhuma) — o que reduziria a superfície do problema o bastante pra valer a pena.

## Iteração 6 (12/08) — remedição de confiança (n=60) do estado atual de produção

Depois de pausar a via de busca, redirecionei o esforço para uma remedição mais confiável: `agent/deck.csv` (= `grass_v5`) + política atual (com a correção de tipo de energia da iteração 1) contra os 9 arquétipos reais, **60 partidas cada** (o dobro do padrão usado nas medições anteriores desta rodada, que oscilaram bastante — ver iterações 1-2).

| Adversário | Uso | Winrate (n=60) |
|---|---|---|
| `munkidori_impidimp` | 21.4% | 72% |
| `abra_kadabra_alakazam` | 16.6% | 70% |
| `dunsparce_dudunsparce` | 14.8% | 67% |
| `dwebble_crustle_kangaskhan` | 8.5% | 13% |
| `cynthias-roselia_gible` | 5.8% | 63% |
| `grookey_thwackey_applin` | 5.3% | 90% |
| `ogerpon_chikorita-meganium` | 4.5% | 40% |
| `dreepy_dragapult` | 3.5% | 85% |
| `ogerpon_solo` | 2.5% | 8% |

**Winrate ponderado: 62.1%** — número mais confiável que os 59.8%/68.2%/58.9% medidos antes a n=35 (todos dentro da mesma faixa de ruído, agora com um centro mais claro em torno de **60-65%**, não 68%). Não muda a conclusão de fundo (critério de 80% não atingido, famílias Ogerpon e Kangaskhan seguem comprometidas), mas é uma base mais sólida para julgar qualquer mudança futura — qualquer nova promoção deveria mover esse número em pelo menos alguns pontos percentuais além do que ruído de amostra explicaria, dado o que já vimos de variância entre execuções.

**Sem mudança em produção** — só uma remedição, nenhuma alteração de código.

## Iteração 7 (12/08) — Crushing Hammer: melhoria ampla, promovida e submetida

Com a via de busca pausada, voltei para deck guiado por dados: `Crushing Hammer` (id 1120, item — "Flip a coin. If heads, discard an Energy from 1 of your opponent's Pokémon.") é a própria carta de disrupção que o deck Kangaskhan (nosso pior matchup) usa contra nós. Hipótese: incluí-la no nosso deck deveria atrasar genericamente qualquer oponente que dependa de acumular energia — o que descreve quase todo o campo, não só o Kangaskhan.

**Deck testado** (`grass_v11_hammer.csv`): `agent/deck.csv` anterior com `Energy Search`×4 → `Crushing Hammer`×4 (única mudança).

**Resultado nos dois matchups-alvo primeiro** (n=60, antes de gastar tempo no sweep completo): Kangaskhan **13%→35%** (mais que dobrou), Ogerpon solo **8%→13%**. Sinal forte o bastante para justificar o sweep completo.

**Sweep completo** (n=60 nos 9 arquétipos reais, n=30 nos 5 sintéticos antigos):

| Adversário | Uso | Antes (n=60, iteração 6) | Depois (`+Crushing Hammer`) |
|---|---|---|---|
| `munkidori_impidimp` | 21.4% | 72% | 77% |
| `abra_kadabra_alakazam` | 16.6% | 70% | 83% |
| `dunsparce_dudunsparce` | 14.8% | 67% | 80% |
| `dwebble_crustle_kangaskhan` | 8.5% | 13% | **35%** |
| `cynthias-roselia_gible` | 5.8% | 63% | 65% |
| `grookey_thwackey_applin` | 5.3% | 90% | 90% |
| `ogerpon_chikorita-meganium` | 4.5% | 40% | 33% |
| `dreepy_dragapult` | 3.5% | 85% | 87% |
| `ogerpon_solo` | 2.5% | 8% | 13% |
| Fighting/Darkness/Psychic/Water-evo (sintéticos, n=30) | — | ~68-92% | 77-90% (todos saudáveis) |
| Fire (sintético, contra-tipo estrutural) | — | ~20% | 23% (ruído, contra-tipo aceito) |

**Winrate ponderado: 62.1% → 70.5%** (+8.4pp). 8 de 9 matchups reais melhoraram ou empataram; só `ogerpon_chikorita-meganium` caiu (40%→33%, ainda dentro de ruído plausível dado tudo que já vimos de variância). Nenhuma regressão nos sintéticos. **Esta foi a melhoria de deck mais ampla e consistente desde o início da sessão** — ao contrário das trocas anteriores (Celebi→Virizion ajudou uns matchups e não outros), disrupção de energia ajuda genericamente porque quase todo arquétipo do campo depende de acumular energia.

**Promovido**: `grass_v11_hammer.csv` → `agent/deck.csv`. Critério 2 de `docs/10` (nenhum arquétipo ≥10% de uso <30% winrate): a família Kangaskhan (variante testada, 8.5% de uso) agora está em 35%, **acima do limiar** — deixa de violar o critério isoladamente (a família mais ampla, ~10.1% agregando sub-variantes não testadas individualmente, seria preciso reconferir, mas o sinal é bom). A família Ogerpon (~11.8%) continua abaixo de 30% nas duas variantes testadas (13-33%) — segue violando.

**Empacotado e submetido como v8**: validado isoladamente (deck extraído do pacote confere com `agent/deck.csv`), enviado ao Kaggle. Justificativa para submeter agora (mesmo com critério 1 de 80% ainda não batido, agora em 70.5%): ganho real, amplo, validado com n=60 (padrão mais rigoroso adotado nesta rodada), sem regressão em nada testado — represar não faz sentido dado que temos folga de prazo e cota de submissão.

## Iteração 8 (12/08) — achado de design: ataques que escalam com energia do próprio ativo; tentativa de contramedida revertida, e um alerta metodológico sério

**Achado de design (não é bug, é como o `Teal Mask Ogerpon ex` foi desenhado)**: lendo o texto do ataque "Myriad Leaf Shower" (o único ataque do `Teal Mask Ogerpon ex`, `attackId=120`): *"This attack does 30 more damage for each Energy attached to both Active Pokémon."* — o dano escala com a energia anexada nos **dois** ativos somados, incluindo o nosso. Ou seja, quanto mais tentamos revidar anexando energia no nosso próprio ativo, mais forte fica exatamente o ataque que nos ameaça — o oposto do que a intuição normal de "desenvolver energia = progresso" sugere. Busquei no pool inteiro e encontrei **44 ataques** com alguma forma de escala por energia (nem todos no mesmo formato — alguns escalam com a energia do ativo do oponente do ponto de vista de quem ataca, ex.: `Alakazam`/"Psychic": *"does 50 more damage for each Energy attached to your opponent's Active Pokémon"*, que do nosso lado significa **nossa** energia).

**Tentativa de contramedida** (`_defender_scales_with_active_energy` + penalidade em `_score_attach`, não commitada — revertida ao final): detecta por texto do ataque se o ativo do oponente tem esse tipo de escala e, se sim, desincentiva anexar energia no nosso próprio ativo (prefere o banco), contanto que tenhamos banco disponível.

**Primeira versão** (detecta tanto "escala com o ativo do oponente" quanto "escala com os dois ativos" — pega `Ogerpon` e `Alakazam`/Psychic): `ogerpon_chikorita-meganium` melhorou bem (33%→47%), mas quase tudo mais piorou, inclusive matchups sem nenhuma relação óbvia com a mudança (`abra_kadabra_alakazam` 83%→73%, `dwebble_crustle_kangaskhan` 35%→20%, `dunsparce_dudunsparce` 80%→65%). Ponderado geral: 70.5%→63.3%.

**Segunda versão, mais restrita** (só "escala com os dois ativos" — não deveria mais afetar o matchup do Alakazam nem do Kangaskhan, que não têm esse padrão específico): `ogerpon_chikorita-meganium` continuou melhor (47%→38%, ainda acima do 33% original), MAS os matchups de **controle** (que não deveriam ser afetados pelo código, já que a condição não dispara para eles) também mudaram bastante: `abra_kadabra_alakazam` caiu para **58%** (era 83% na iteração 7, 73% na primeira tentativa) e `dwebble_crustle_kangaskhan` caiu para **25%** (era 35%).

**Achado metodológico importante (mais sério que o resultado do experimento em si)**: matchups de controle — cujo código de decisão é **idêntico** ao commitado — variaram **25+ pontos percentuais** entre execuções, mesmo a n=60. Isso confirma que o ruído amostral nesses matchups específicos (`abra_kadabra_alakazam`, `dwebble_crustle_kangaskhan`) é maior do que o já mapeado nas iterações anteriores — n=60 **não é suficiente** para isolar mudanças com efeito menor que ~20-25 pontos percentuais nesses arquétipos especificamente. Qualquer conclusão futura sobre esses dois matchups específicos precisa ou de N bem maior (100+) ou de múltiplas repetições comparadas, não uma única leitura mesmo que "grande".

**Decisão**: revertido (`git checkout -- agent/policy_heuristic.py`) — o sinal está confuso demais para promover com confiança, e o princípio do projeto é não afirmar ganho que os dados não sustentam. O achado de **design** (ataques que escalam com energia do ativo) continua válido e documentado — fica como ideia para retomar no futuro, mas exigindo uma metodologia de validação mais robusta (N maior, ou testado isoladamente contra um oponente sintético construído especificamente com esse tipo de ataque, para isolar o efeito do ruído de matchup).

**Sem mudança em produção** — nenhuma submissão gasta nesta iteração.

## Próximos passos identificados para as próximas iterações do loop

1. **API nativa de busca** (`search_begin`/`search_step`/`search_end`/`search_release`, `vendor/cg/api.py`) — ainda não investigada tecnicamente nesta sessão apesar de citada repetidas vezes como o caminho estruturalmente correto para o problema do Kangaskhan (nocaute em 1 golpe, sem resposta possível por heurística reativa) e do Ogerpon (jogo termina rápido demais para heurística reagir). Próxima iteração: ler a assinatura real da API e avaliar viabilidade de um lookahead mínimo (mesmo que só 1-ply) dentro do orçamento de tempo por jogada (temos folga enorme: latência medida da heurística atual é ~1ms, contra um limite de tempo que nem sabemos se existe — ver `docs/06` item 5).
2. Se a busca não for viável a tempo, considerar aceitar as duas famílias de matchup fracas como teto estrutural do approach atual e redirecionar esforço para robustez/consistência geral (reduzir variância, não só subir a média).
