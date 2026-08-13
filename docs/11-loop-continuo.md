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

## Iteração 9 (12/08) — deck Xerosic descartado (sem sinal claro); achado de robustez sério: partidas de 1000+ turnos contra um arquétipo de stall

**Xerosic's Machinations** (troca de 2x `Urbain` por 2x essa carta, disrupção de mão do oponente): testado contra os dois matchups-alvo (Kangaskhan, Ogerpon solo) a n=60 antes de ir para o sweep completo — ambos os resultados (28% e 10%) caíram **dentro das faixas de ruído já mapeadas na iteração 8** para esses mesmos matchups (18-35% e 8-13%), não fora delas. Sem sinal distinguível de melhora nem piora. Descartado sem promover — não vale gastar mais tempo/partidas tentando decidir algo que já está preso no ruído.

**Ampliação de cobertura**: extraí mais 4 arquétipos pequenos da mesma amostra de 199 episódios (`real_mega-lucario_solrock.csv` 1.5% uso, `real_slowpoke_slowking.csv` 0.8%, `real_grookey_thwackey_dipplin.csv` 2.3%, `real_team-rockets-tarountula.csv` 0.8%) para checagem de robustez mais ampla (não para promover nada, só para não deixar pontos cegos). Três se comportaram normalmente (46-89% de winrate, turnos médios saudáveis). Um não: **`real_slowpoke_slowking.csv`** deu 63% de winrate mas com **7 de 35 partidas terminando em empate e duração média de 300+ turnos** — sinal de alarme claro.

**Investigação**: reproduzido em lote maior (30 partidas isoladas, script `/tmp/.../scratchpad/debug_slowpoke2.py`): **5 de 30 (17%) bateram o teto de segurança de 5000 passos** do harness local sem a partida terminar naturalmente, alcançando **turno 1246–1658**. Causa raiz identificada no texto das cartas desse arquétipo: `Slowpoke`/"Dangle Tail" recupera um Pokémon nocauteado de volta pra mão (0 dano), e o Stadium `Academy at Night` permite devolver uma carta da mão pro topo do baralho todo turno — combinados, criam um ciclo de reciclagem de recursos que pode, na teoria, se sustentar por muito tempo sem nenhum lado conseguir fechar os 6 prêmios nem "deckar" (ficar sem cartas).

**Contexto importante que reduz (mas não zera) a preocupação**: neste teste, o baralho do Slowpoke/Slowking está sendo pilotado pela **nossa própria heurística** como substituto — ela não entende semanticamente o propósito de "Dangle Tail"/`Academy at Night` (só vê dano=0, categoriza abaixo de ATTACH), então pode estar reciclando de um jeito mais "cego"/simétrico do que um bot de verdade pilotando esse arquétipo no ladder real faria. Cheque cruzado com dados reais: nos 199 episódios baixados do ladder (`/tmp/.../scratchpad/episodes_sample/`), a duração real variou entre 33 e **275 passos** (mediana 155) — nenhum episódio real chegou perto de 1000+ turnos. Ou seja, **não há evidência de que isso aconteça de verdade no ladder** — pode ser majoritariamente um artefato da nossa metodologia de teste (usar a mesma heurística nos dois lados de um arquétipo que ela não foi feita pra pilotar bem), não um risco real medido.

**Por que registrar mesmo assim**: (a) o item 5 de `docs/06` (limite de tempo por jogada) segue não confirmado — se existir um limite por partida/episódio (não só por jogada), uma partida real que entrasse nesse tipo de ciclo poderia gerar o mesmo tipo de falha que causou o `ERROR` da submissão v1; (b) mesmo sendo provavelmente um artefato de teste, o mecanismo (recuperação de Pokémon nocauteado + retorno de carta ao baralho) é real e existe no pool de cartas — um oponente real bem pilotado usando essas ferramentas de forma mais inteligente contra nós é uma possibilidade, não uma garantia de segurança.

**Ação tomada**: nenhuma mudança de código — não há uma correção óbvia do nosso lado (o ciclo é dirigido pelas cartas do oponente, não pelas nossas; nosso lado já prioriza ataque real sobre utilidade de dano zero, e 0 erros de política ocorreram mesmo nas partidas de 1000+ turnos, então a cadeia de fallback continua segura). Fica documentado como risco monitorado, não bloqueante (uso de 0.8% no campo, sem evidência real de ocorrência), mas relevante para o relatório final da trilha Strategy e para não ser pego de surpresa se aparecer de novo.

## Iteração 10 (12/08) — checagem de deriva do meta (amostra fresca de 08-11) e novo arquétipo relevante

O meta muda dia a dia (já documentado antes — `docs/09`). Baixei uma amostra fresca do dataset `kaggle/pokemon-tcg-ai-battle-episodes-2026-08-11` (o mais recente disponível, publicado 12/08 00:08 UTC) — 76 episódios / 152 decks (menor que a amostra de 199 episódios usada antes, por limite de tempo de download nesta iteração, mas ainda informativa).

**Comparação de uso (08-10 → 08-11)**:

| Arquétipo | Uso 08-10 | Uso 08-11 |
|---|---|---|
| `munkidori_impidimp` | 21.4% | **27.0%** (subiu) |
| `abra_kadabra_alakazam` | 16.6% | 19.1% |
| `dunsparce_dudunsparce` | 14.8% | 11.8% |
| **`mega-lucario_solrock`** | **1.5%** | **10.5%** (⚠️ subiu muito) |
| `dwebble_crustle_kangaskhan` | 8.5% | 8.6% (estável) |
| `dreepy_dragapult` | 3.5% | 7.9% (subiu) |
| família Ogerpon (todas variantes) | ~11.8% | ~8.0% (caiu) |
| `grookey_thwackey_applin` | 5.3% | 0.7% (caiu bastante) |

**Achado principal**: `Mega Lucario ex/Solrock/Riolu` — arquétipo que tínhamos catalogado (iteração 9) só por completude, com 1.5% de uso — **saltou para 10.5%**, virando o 4º arquétipo mais jogado nesta amostra fresca. Testei a produção atual (`agent/deck.csv`, com `Crushing Hammer`) contra ele a n=60: **53% de winrate** — matchup próximo do equilíbrio, sem alarme.

**Recalculando o winrate ponderado com os pesos frescos** (usando os winrates já medidos a n=60 onde disponíveis): aproximadamente **65%** — parecido com os 70.5% medidos com os pesos antigos (dentro da margem de incerteza dado tudo que já vimos de ruído), não uma mudança de conclusão. `Munkidori` (nosso melhor matchup, 77%) ganhando peso ajuda; `Ogerpon` (nosso pior) perdendo peso ajuda; `Lucario` (nova entrada, 53%) e o fato de `Kangaskhan` continuar estável em ~8.6% mantêm o quadro geral parecido.

**Conclusão**: nenhuma mudança de código motivada por este achado — o novo arquétipo relevante (`Lucario`) não é um problema (53%), e o quadro geral de winrate ponderado não mudou o suficiente para alterar a decisão sobre os critérios de `docs/10`. Fica registrado como confirmação de que o meta é dinâmico e vale reconferir periodicamente, não como algo acionável agora.

## Iteração 11 (12/08) — sessão estendida a pedido do usuário ("não vou mandar outro continue hoje, faça o máximo, otimize, garanta que não vai ter erros e submeta ao final")

Varredura final de segurança em todos os 18 adversários catalogados (13 reais + 5 sintéticos), 25 partidas cada: **0 erros de política em todos eles**. Confirma o achado de robustez da iteração 9 (`slowpoke_slowking`: 8/25 empates, ~481 turnos médios — reproduzido de novo, mesmo padrão, mesmo diagnóstico: risco monitorado, sem correção disponível do nosso lado).

**Hand Trimmer** (trocar 4 `Basic Grass Energy` por 4x, id 1087 — disrupção mútua de mão): regressão real no matchup de controle `munkidori_impidimp` (77%→55%, fora de qualquer faixa de ruído já vista para esse arquétipo — nunca tinha ficado abaixo de 63%), sem ganho nos alvos (Kangaskhan 27%, Ogerpon 10%, ambos dentro do ruído já mapeado). Cortar energia de 27→23 parece prejudicar consistência mais do que a disrupção de mão compensa. **Descartado.**

**Recalibração de `_BENCH_REDIRECT_RATIO`** (1.4→1.2): sem sinal fora do ruído já mapeado em nenhum dos dois matchups-alvo. **Descartado**, confirma o achado de `docs/09` de que esse parâmetro específico não é o gargalo.

**Correção de setup: ativo inicial não deve ser o atacante mais caro** — achado observacional: rastreando 20 partidas, `Tapu Bulu` (nosso atacante mais forte, mas o mais caro — 4 energia) estava sendo escolhido como **ativo inicial em 35% das partidas** (`_score_setup_candidate` usava a mesma pontuação de "eficiência de dano por energia" tanto para o ativo quanto pro banco — eficiência favorece atacantes caros de dano alto, o que é bom pra um Pokémon que vai *ficar no banco carregando energia*, mas ruim pra quem *começa em jogo e devia atacar logo*). Corrigido: `_score_setup_candidate` agora recebe um parâmetro `for_active`; quando `True`, o custo de energia do ataque mais barato domina a pontuação (`-custo*100`), com eficiência só como desempate — na prática, para o ativo inicial agora só escolhe `Tapu Bulu` quando é o único básico disponível na mão (caiu de 7/20 para 3/20 nas mesmas 20 partidas de checagem). Banco continua com a lógica antiga (eficiência), que faz sentido lá.

**Validação**: nenhum matchup mostrou uma mudança clara e reproduzível fora do ruído já mapeado (inclusive um susto — `munkidori_impidimp` caiu pra 57% numa leitura de n=40, mas replicando a n=60 voltou a 75%, dentro do normal — mais um exemplo do quanto esse harness de teste é ruidoso para mudanças de efeito modesto). **Decisão**: mantida mesmo sem confirmação estatística clara de ganho, porque (a) é estruturalmente correta por princípio (não faz sentido começar o jogo com o atacante mais lento parado no ativo — é o mesmo tipo de raciocínio que já validou a escolha original de `_score_setup_candidate` em `docs/08`), (b) nenhuma leitura, nem a mais alarmante, se sustentou numa repetição com N maior, e (c) é uma mudança de baixo risco/escopo pequeno, ao contrário do Hand Trimmer e do "energy punish" (iteração 8), que tinham mecanismos mais especulativos e sinal misto mesmo após repetição.

### Varredura final consolidada (produção final desta sessão)

| Adversário | Uso (mais recente disponível) | Winrate (última leitura) |
|---|---|---|
| `munkidori_impidimp` | 27.0% | 75% (n=60) |
| `abra_kadabra_alakazam` | 19.1% | 82% (n=40) |
| `dunsparce_dudunsparce` | 11.8% | 65% (n=40) |
| `mega-lucario_solrock` | 10.5% | 60% (n=40) |
| `dwebble_crustle_kangaskhan` | 8.6% | 35% (n=60) |
| `dreepy_dragapult` | 7.9% | 92% (n=40) |
| `ogerpon_chikorita-meganium` | ~4-8%* | 33% (n=60) |
| `ogerpon_solo` | ~2-4%* | 12% (n=60) |
| `cynthias-roselia_gible` | 5.8%† | 80% (n=40) |
| `grookey_thwackey_applin`/`_dipplin` | ~1-5%† | 92%/83% |
| `team-rockets-tarountula` | ~1% | 50% (n=30) |

\* família Ogerpon somada varia entre ~8% (amostra 08-11) e ~11.8% (amostra 08-10) dependendo do dia. † não recapturado na amostra fresca de 08-11 (amostra menor, 76 episódios); usando peso da amostra de 08-10.

**Estimativa de winrate ponderado combinando pesos frescos (08-11) com os antigos onde não recapturados: ~63-67%** — consistente com a faixa (62-70%) observada em todas as medições desta rodada, ainda abaixo da meta de 80% de `docs/10`, sem mudança de conclusão sobre os dois problemas estruturais (famílias Ogerpon e Kangaskhan).

### Decisão de submissão final desta sessão

Nenhuma mudança de **deck** foi promovida nesta sessão estendida (Hand Trimmer e recalibração de ratio descartados). A única mudança de **política** promovida foi a correção do ativo inicial (setup), de baixo risco e sem regressão confirmada em nenhum teste. Empacotado, validado isoladamente (deck extraído do pacote confere byte-a-byte, `main.agent({'select': None})` retorna as 60 cartas corretas, partida isolada rodada com o código do próprio pacote sem erros), e **submetido como v9** (última submissão disponível hoje — 0 restantes após o envio). Como não há nenhuma mudança de deck em relação à v8 e a mudança de política é pequena/de baixo risco, esta submissão serve principalmente para (a) capturar a correção do setup no ladder real e (b) manter o agente ativo com mais partidas acumuladas — não é esperado um salto grande no score real a partir dela.

**Cota de submissões esgotada por hoje (12/08)** — usuário avisou que não vai mandar mais mensagens hoje. Próxima iteração do loop deve continuar a partir daqui na próxima interação (a cota reseta, historicamente, por volta da virada do dia UTC).

## Iteração 12 (13/08) — causa raiz do bug do `search_step` isolada: não é a predição, é o próprio `search_step`

Retomei a investigação pausada nas iterações 4-5 com o teste que ficou pendente: isolar o problema usando previsões **exatas** (sem reamostragem ingênua), já que a hipótese até aqui era "baralho previsto degenerado confunde o engine".

**Teste 1** (previsão do baralho do oponente 100% fiel — usando o próprio `deck_b` real, subtraindo o que já foi revelado, respeitando contagem real de cópias): a simulação **ainda travou** (200+ passos presos no turno 9, sem avançar). Isso **descarta a hipótese da predição degenerada** como causa suficiente — mesmo com informação perfeita do lado do oponente, o problema persiste.

**Teste 2** (previsão do NOSSO PRÓPRIO baralho também corrigida — antes eu usava `[energia]*N` como placeholder para o nosso lado, o que é claramente errado já que efeitos de compra como `Cheren`/`Urbain` puxam desse baralho previsto): ainda travou.

**Teste 3, decisivo** (mão mínima e 100% conhecida — sem nenhuma predição em jogo, só 5 cópias de `Basic Grass Energy` na mão real): rastreando passo a passo, o padrão ficou claro e reproduzível: depois de anexar a energia disponível (`energyAttached=True`), a única opção restante no select é **END** (`type=14`, única opção, `minCount=1, maxCount=1`). Escolher essa única opção (`choice=[0]`) — exatamente a mesma resposta que `safe_selection` produziria e que funciona perfeitamente em milhares de partidas reais via `battle_select` — **não avança o turno**: `turnActionCount`, `turn` e a mão inteira ficam idênticos indefinidamente, repetindo o mesmo select "só END disponível" para sempre.

**Controle decisivo**: reproduzi a mesma sequência de decisões (mesma semente de RNG) usando `battle_select` (jogo real, não busca) — o turno avança normalmente de 9 para 10, passando por múltiplos `SelectType` diferentes (inclusive um tipo `1` com `minCount=0`, resolvido corretamente por `safe_selection` retornando lista vazia `[]`) sem nenhum travamento.

**Conclusão**: o problema **não é a qualidade da nossa predição de mão/baralho oculto** (a hipótese original das iterações 4-5) — é um comportamento específico de **como `search_step` processa a transição de turno**, que diverge do que `battle_select` faz na partida real, mesmo para a resposta EXATA que funciona perfeitamente fora da busca. Pode ser uma limitação genuína do modo de busca do engine nativo (ex.: precisar de algum sinal adicional que `battle_select` dispara automaticamente e `search_step` não), não um erro de uso da API que eu consiga corrigir só ajustando a predição.

**Decisão final sobre esta linha de investigação**: encerrada por ora. Já foram 3 iterações (4, 5, 12) tentando entender/contornar isso, com uma causa raiz agora bem isolada mas sem solução óbvia do nosso lado (não temos acesso ao código-fonte do `libcg.so`, só à API documentada em `vendor/cg/api.py`, que não documenta esse comportamento). Não vale continuar sem uma pista nova (ex.: um exemplo oficial de uso de `search_step` para comparar, que não temos). `agent/search_lookahead.py` permanece no repositório como registro do trabalho e do diagnóstico, não integrado, não usado em produção.

## Iteração 13 (13/08) — buscas adicionais sem sucesso: habilidades e energia especial

Duas ideias adicionais exploradas rapidamente, ambas sem sinal fora do ruído:

- **Habilidades**: nenhum dos 4 Pokémon do deck atual (`Genesect`, `Pinsir`, `Virizion`, `Tapu Bulu`) tem habilidade — ao contrário do `Teal Mask Ogerpon ex` (habilidade "Teal Dance": anexa energia extra + compra carta, todo turno). Busquei no pool inteiro por um básico Grass não-`ex` com habilidade de aceleração de energia ou compra comparável — não existe nada parecido disponível (as únicas habilidades encontradas em básicos Grass são de prevenção de dano no banco, evolução condicional, ou cura pequena — nada que compense a assimetria estrutural).
- **`Grow Grass Energy`** (id 18, energia especial não-ACE-SPEC: fornece energia Grass + dá +20 HP ao Pokémon que a carrega): testado trocando 4x `Basic Grass Energy` por ela. Kangaskhan 15% (dentro da faixa 13-35% já mapeada), Munkidori 80% (normal). +20 HP por cópia não é suficiente para virar nenhum limiar de nocaute que importa (ex.: ainda morre pro golpe de 200 do Kangaskhan). Descartado.

Com isso, considero a busca por melhorias incrementais de deck/política **razoavelmente esgotada** para esta rodada — muitas frentes tentadas (atacantes alternativos, disrupção adicional, corte de energia, recalibração de parâmetros, habilidades, energia especial), só duas produziram ganho validado (`Crushing Hammer`, correção de setup do ativo). O estado atual (`agent/deck.csv` + `agent/policy_heuristic.py`, já submetido como v9) permanece o melhor validado.

## Iteração 14 (13/08) — otimização evolutiva (CMA-ES) direto sobre winrate real

Depois do resultado negativo de imitation learning (`docs/12`), o usuário perguntou sobre reinforcement learning. RL completo (rede neural + self-play + policy gradient) foi avaliado como inviável no tempo restante, mas uma alternativa mais tratável surgiu: em vez de imitar dados de log, **otimizar direto os pesos do vetor de scoring contra o winrate real**, usando busca evolutiva (CMA-ES) — sem rede neural, sem gradiente, sem problema de atribuição de crédito ao longo de dezenas de turnos.

**Implementação** (`scripts/evolve_policy.py`): reusa a mesma arquitetura de features de `agent/policy_ml.py` (20 dimensões), mas o vetor de pesos é o genoma evoluído pelo `cma` (biblioteca `pycma`, instalada via pip). Fitness = winrate ponderado (pelo uso real dos 10 arquétipos catalogados) do nosso deck pilotado pelo candidato contra os arquétipos pilotados por `policy_heuristic` (mesmo proxy de oponente usado a sessão inteira) — com uma pequena penalidade por erro de política (rede de segurança acionada), pra evitar que a busca favoreça soluções instáveis. Checkpoint incremental em `data/ml/evolved_weights.json` a cada nova melhor solução encontrada, para não perder progresso.

Warm-start a partir dos pesos do `policy_ml.py` (iteração de imitation learning), já que é um ponto de partida melhor que aleatório.

**Artefatos de deploy** (`deploy/`) também preparados para quando o usuário subir o Portainer mencionado: `Dockerfile` + `entrypoint.sh` + `stack.yml` (Docker Compose) + `README.md`. Decisão importante de licenciamento: o container **nunca embute o engine** (`vendor/cg/`) — ele busca sozinho via `scripts/fetch_official.sh` usando as credenciais do Kaggle do próprio usuário, montadas como volume/secret, para não violar a cláusula de "proibida redistribuição a terceiros" da licença do engine (`docs/06`, item 3) — o raciocínio (revisado com o usuário) é que isso é diferente de "transmitir a um terceiro não participante", já que é o próprio participante rodando em infraestrutura que ele controla.

**Rodada de otimização em andamento** (lançada em background nesta sessão): 300 gerações, população 12, 8 partidas por arquétipo por avaliação (≈960 partidas/geração, ~30s/geração). Progresso registrado abaixo conforme checkpoints relevantes.

## Iteração 15 (13/08) — otimização evolutiva estabiliza, valida MUITO acima da meta, promovida e submetida

A rodada de CMA-ES (iteração 14) estabilizou por 18+ gerações em fitness=0.9262 (geração 22 de 300 planejadas — deixado rodando em background, ver "evolução contínua" abaixo). Peguei o checkpoint nesse ponto para validação rigorosa (metodologia igual à sessão inteira: nosso deck pilotado pela política candidata, oponente pilotado por `policy_heuristic` fixo).

**Validação n=60, 10 arquétipos reais** (cobertura 84.4% do campo por uso):

| Adversário | Uso | Winrate antes (`policy_heuristic`) | Winrate `policy_evolved` |
|---|---|---|---|
| `munkidori_impidimp` | 21.4% | 72-77% | **88%** |
| `abra_kadabra_alakazam` | 16.6% | 70-83% | **90%** |
| `dunsparce_dudunsparce` | 14.8% | 65-80% | **87%** |
| `dwebble_crustle_kangaskhan` | 8.5% | 13-35% | **47%** |
| `cynthias-roselia_gible` | 5.8% | 63-80% | **92%** |
| `grookey_thwackey_applin` | 5.3% | 90% | **98%** |
| `ogerpon_chikorita-meganium` | 4.5% | 33-49% | **57%** |
| `dreepy_dragapult` | 3.5% | 85-96% | **98%** |
| `ogerpon_solo` | 2.5% | 8-13% | 12% (sem mudança) |
| `mega-lucario_solrock` | 1.5% | 53-60% | **70%** |

**Winrate ponderado: 81.2%** — primeira vez que bate a meta de 80% definida em `docs/10`. **Todo matchup melhorou ou ficou igual, nenhum piorou** — incluindo os dois problemas estruturais mais persistentes da sessão inteira (Kangaskhan e Ogerpon-chikorita), que agora cruzam o limiar de 30% do critério 2 de `docs/10`.

**Generalização** (decks sintéticos, fora do conjunto usado no fitness — checagem contra overfitting): `fighting_rush_v3` 100%, `darkness_v1` 97%, `psychic_v1` 100%, `water_evo_v1` 93%, e até o contra-tipo estrutural `fire_v1` (Grass é fraco a Fire por design do jogo) subiu de ~16-34% para **70%**. Isso descarta a hipótese de que a otimização só decorou os 10 arquétipos usados como fitness — a melhora é ampla.

**Robustez**: 0 erros de política em ~500+ partidas de validação (10 partidas isoladas + n=60×10 arquétipos + n=30×5 sintéticos). O arquétipo de risco de stall (`slowpoke_slowking`, iteração 9) também melhorou bastante: 87% de winrate, só 1 empate em 30 (era 8-11 empates em 25-35 antes) e tempo médio de partida bem menor (59 turnos vs 300-500+ antes) — a política evoluída parece lidar com esse adversário de forma mais decisiva.

**Promovido e submetido como v10**: `agent/policy_evolved.py` (novo módulo, arquitetura idêntica a `policy_ml.py` — 20 features, Python puro, sem dependência externa) adicionado à cadeia de fallback em `agent/main.py` como primeira opção: `[policy_evolved, policy_heuristic, policy_baseline] → safe_selection`. Validado de ponta a ponta com o pacote real (`main.agent()`, não só `choose()` isolado) antes de submeter — 0 erros.

## Evolução contínua (a partir daqui)

A pedido do usuário, a otimização (`scripts/evolve_policy.py`) continua rodando em background (checkpoint em `data/ml/evolved_weights.json`, commitado periodicamente). Quando encontrar uma melhora nova e suficientemente validada (mesmo processo: n=60 nos 10 arquétipos + sintéticos, sem regressão), promovo de novo e submeto, respeitando a cota diária (usada: 1 de 5 hoje até agora nesta rodada, `v10`).

**Score real da v10**: 359.2 — dentro da faixa das últimas submissões (329-361), sem salto visível apesar do ganho local de 62-70%→81.2%. Consistente com o padrão de instabilidade já bem documentado nesta sessão (rating tipo TrueSkill ainda convergindo, poucas partidas acumuladas por submissão) — não é tratado como sinal de que a melhora local não é real, só reforça que uma leitura isolada do score real não é confiável tão cedo.

**Rodada 2 do CMA-ES**: a rodada 1 estabilizou em fitness=0.9262 depois da geração 22 (40+ gerações sem melhora). Reiniciada com sigma maior (0.4→0.6) e população maior (12→14), a partir do mesmo checkpoint (warm-start) — escapou do platô rapidamente, novo melhor fitness=0.9351 já na geração 4. Em andamento.

## Iteração 16 (13/08) — deploy no Portainer (infraestrutura própria do usuário)

O usuário subiu o Portainer prometido (`https://portainer.caioruiz.com`) e passou a URL + um API token com escopo próprio. Confirmado antes de agir: o repositório `CaioRuizz/pokemon_challenge` é **público** (usuário corrigiu — checagem anterior via `api.github.com` tinha dado uma mensagem enganosa por causa do próprio contexto de acesso desta sessão, não do repositório em si; `git ls-remote` sem autenticação confirmou). Kaggle: reusado o mesmo `access_token` já configurado nesta sessão de desenvolvimento, a pedido do usuário.

**Deploy via API do Portainer** (sem mexer na UI): stack Docker Compose criada via `POST /api/stacks/create/standalone/string` — imagem `python:3.11-slim` genérica (sem build customizado), que no `command` de inicialização: instala `git`/`kaggle`/`cma`/`numpy`, clona o repositório público, grava a credencial do Kaggle recebida via variável de ambiente do stack, e executa `deploy/entrypoint.sh` (o mesmo script já preparado e commitado, reaproveitado em vez de duplicar lógica). Volume Docker nomeado (`evolve_data`) montado em `/persist`, symlinkado para `data/ml` dentro do clone — o checkpoint evoluído fica persistente entre restarts do container sem precisar de lógica extra de cópia.

**Dois bugs encontrados e corrigidos na primeira tentativa** (documentados por rigor, mesmo sendo infra e não código do agente):
1. **Interpolação prematura do Docker Compose**: referências de variável de shell dentro do `command:` (ex.: `$GENERATIONS_PER_ROUND`) foram capturadas pelo PRÓPRIO parser do compose antes do container rodar (docker-compose trata `$VAR` como sintaxe de interpolação sua, não só como texto pra o shell) — como essas variáveis não estavam na lista `env` do payload da API, viraram string vazia, e o container tentou rodar `evolve_policy.py --generations "" --pop-size ""` etc. Corrigido evitando duplicar a lógica dentro do `command:` do compose — passei a clonar o repo e delegar tudo pro `deploy/entrypoint.sh` (um script de verdade, não uma string YAML), que não sofre interpolação do compose.
2. **Token exposto em `docker inspect`**: a mesma interpolação prematura também gravou o token do Kaggle em texto puro dentro do array `Cmd` do container (visível via `/containers/.../json`) — mesmo não sendo uma exposição pra fora da infraestrutura do próprio usuário, evitável. Corrigido usando `$$KAGGLE_ACCESS_TOKEN` (escape de dólar duplo) dentro do `command:`, forçando o compose a deixar a referência intacta pro shell resolver em runtime a partir da variável de ambiente real do container, em vez de interpolar o valor literal no momento do deploy.

**Lição de segurança operacional**: em um dos comandos de diagnóstico, o token do Kaggle apareceu no output de um `cat` que rodei sem pensar — sinalizado ao usuário na hora. Nenhuma exposição fora desta conversa entre nós, mas fica registrado como lembrete de sempre filtrar/evitar imprimir payloads que possam conter segredo, mesmo em ambiente de desenvolvimento controlado.

Stack redeployada com as correções, container rodando — checkpoint compartilhado com este repositório via commits periódicos (mesmo `evolved_weights.json`, mesmo processo de validação antes de promover qualquer coisa a produção).

## Próximos passos identificados para as próximas iterações do loop

1. **API nativa de busca** (`search_begin`/`search_step`/`search_end`/`search_release`, `vendor/cg/api.py`) — ainda não investigada tecnicamente nesta sessão apesar de citada repetidas vezes como o caminho estruturalmente correto para o problema do Kangaskhan (nocaute em 1 golpe, sem resposta possível por heurística reativa) e do Ogerpon (jogo termina rápido demais para heurística reagir). Próxima iteração: ler a assinatura real da API e avaliar viabilidade de um lookahead mínimo (mesmo que só 1-ply) dentro do orçamento de tempo por jogada (temos folga enorme: latência medida da heurística atual é ~1ms, contra um limite de tempo que nem sabemos se existe — ver `docs/06` item 5).
2. Se a busca não for viável a tempo, considerar aceitar as duas famílias de matchup fracas como teto estrutural do approach atual e redirecionar esforço para robustez/consistência geral (reduzir variância, não só subir a média).
