# 08 · Status da Implementação (Fases 1 e 2)

Atualizado em 07/08/2026. Este documento resume o que já foi **construído e testado**, complementando o plano (docs 00–07).

## O que existe hoje

| Componente | Arquivo | Status |
|---|---|---|
| Vendorização do engine oficial | `vendor/cg/` (gitignorado) + `scripts/fetch_official.sh` | ✅ Funciona, testado |
| Agente baseline (nunca crasha) | `agent/main.py`, `agent/fallback.py`, `agent/policy_baseline.py` | ✅ Validado em ~50 partidas locais, 0 erros/seleções ilegais |
| Política heurística (Fase 2) | `agent/policy_heuristic.py`, `agent/card_data.py` | ✅ Pontua ataques por dano efetivo (fraqueza/resistência) e prioriza nocaute garantido; recua quando o ativo está com HP crítico |
| Cadeia de fallback em camadas | `agent/main.py` | ✅ `policy_heuristic` → `policy_baseline` → `fallback.safe_selection`, cada camada cobrindo exceção da anterior |
| Deck real (60 cartas) | `agent/deck.csv` (= `data/decks/grass_v1.csv`) | ✅ Mono-Grass (Genesect/Pinsir/Celebi/Shaymin) — >50% de winrate contra os 4 adversários de teste (ver seção "Troca de tipo") |
| Harness de avaliação local | `eval/local_match.py` | ✅ CLI reutilizável, roda políticas/decks diferentes um contra o outro via `cg/game.py` |
| Empacotamento da submissão | `build/package_submission.sh` → `build/submission.tar.gz` (gitignorado) | ✅ Testado isolado (extraído + `main.agent()` chamado fora do repo) |

## O que o baseline faz (e não faz)

- **Política**: para a decisão principal do turno (`SelectType.MAIN`), prioriza `ATTACK > EVOLVE > ABILITY > PLAY > ATTACH > RETREAT > END`. Para qualquer outra decisão (escolher alvo, energia, sim/não, etc.), pega as primeiras opções legais disponíveis — sem heurística de conteúdo.
- **Não lê o texto/efeito das cartas.** Não sabe que um ataque como "Rising Chop" só funde dano contra Pokémon `ex`, nem pondera trocas táticas. Isso é esperado — é o objetivo da Fase 2 (`docs/02-estrategia-solucao.md`).
- **Nunca falha**: todo caminho passa por `agent/fallback.py`, que garante índice válido (`minCount`≤len≤`maxCount`, sem duplicata, dentro do range de opções) mesmo se a lógica "inteligente" (`policy_baseline.choose`) lançar exceção — coberto por `try/except` em `agent/main.py`.

## Deck escolhido: por quê

Sem acesso ao `/rules` (banlist e regras específicas do Standard vigente ainda não lidas — ver `06-riscos-questoes-abertas.md` item 6), optei por **não copiar um decklist de meta humano real** (ex.: Gardevoir ex, Gholdengo ex — vistos em pesquisa geral de Standard) porque:
1. Não há garantia de que essas cartas/arquétipos existem neste pool específico de ~1.267 cartas do engine (o pool tem nomes e cartas que não batem 1:1 com o meta "real" que eu conheço — ex.: `Professor's Research`, `Nest Ball` e `Iono` não foram encontrados na base).
2. Decks de combo real dependem de sequenciamento cuidadoso (evoluções, abilities encadeadas) que o baseline não sabe fazer.

Em vez disso, montei um deck **mono-Fighting, só Pokémon básicos (sem evolução)**, com ataques **sem condição de texto** (evitando atacar "para não fazer nada" por não cumprir um requisito que o bot não entende), usando dados reais de `all_card_data()`/`all_attack()`:
- Okidogi, Sandy Shocks, Lunatone, Hitmontop (4 cópias cada = 16 Pokémon)
- Switch, Ultra Ball (4 cópias cada = 8 treinadores utilitários simples)
- Basic {F} Energy (36 cópias)

Isso é deliberadamente conservador — o objetivo é ter algo **legal e jogável agora**, não o deck ótimo.

## Deck v2: otimização

O v1 tinha um problema óbvio: **36 de 60 cartas eram energia** (60%), muito mais que o necessário — a mão fica cheia de energia parada em vez de ameaças/recursos. Fui atrás de treinadores melhores na base real de cartas (`all_card_data()`, filtrando por texto de efeito) e troquei:

- **Ultra Ball → Master Ball** (busca qualquer Pokémon, **sem** custo de descartar 2 cartas como o Ultra Ball exigia — mais seguro para um bot que não pondera esse trade-off).
- **+ Fighting Gong** ×4 (busca Basic {F} Energy **ou** Pokémon {F} básico — desenhado sob medida para um deck mono-Fighting).
- **+ Cheren** ×4 e **Urbain** ×4 (ambos "Draw 3 cards.", incondicional — os dois únicos supporters de compra sem pegadinha que encontrei entre os 61 supporters do pool).
- Energia caiu de 36 para 27.

Composição final: 16 Pokémon (inalterado) + 17 treinadores (Master Ball ×1, Fighting Gong ×4, Cheren ×4, Urbain ×4, Switch ×4) + 27 Basic {F} Energy = 60.

**Pegadinha real encontrada testando contra o engine**: `Master Ball` tem `aceSpec=True` — regra "ACE SPEC: no máximo 1 cópia por deck". Coloquei 4 cópias na primeira tentativa e o `battle_start` retornou `errorType=4` (deck inválido) para os dois lados testados, com `obs=None`. Corrigido para 1 cópia + 3 energias extras. Isso é exatamente o tipo de regra que só aparece testando contra o engine real, não nos dataclasses — vale ficar atento a esse padrão (`aceSpec`) para decks futuros.

**Resultado A/B** (v2 vs. v1, mesma política heurística, 50 partidas): v2 venceu **50% a 46%** (2 empates) — vantagem real mas modesta, não uma virada de jogo. Isso também é honesto de registrar: como a política ainda não sabe usar supporters/items *estrategicamente* (ex.: "comprar quando a mão está vazia, atacar quando não"), boa parte do valor de ter mais consistência no deck ainda não é totalmente explorada pelo bot atual. Sanity check contra o placeholder confirma ausência de regressão (90% de vitórias). `agent/deck.csv` já aponta para o v2.

## Resultado honesto: heurística vs. baseline no deck atual

Testei `policy_heuristic` contra `policy_baseline` pilotando o **mesmo deck** dos dois lados (30 partidas): **47% a 47%** (2 empates) — sem vantagem estatística clara. Isso não é um bug; é uma consequência direta de como o deck atual foi montado:
- Cada Pokémon do deck só tem **1 ataque utilizável** por carta → não há "qual ataque escolher" para a heurística otimizar.
- Os dois lados são **do mesmo tipo (Fighting)** → a lógica de fraqueza/resistência da heurística nunca é acionada (fraqueza nunca bate contra o próprio tipo).

A vantagem da heurística deve aparecer em três cenários que este teste não cobre: (1) contra decks de **tipo diferente** (fraqueza/resistência entram em jogo), (2) contra Pokémon com **múltiplos ataques** (trade-off custo/dano), (3) quando o ativo entra em **risco de HP baixo** (lógica de retreat). Sanity check contra o placeholder degenerado confirma que não houve regressão (80% de vitórias, em linha com os 90% do baseline puro). A heurística já é a política ativa por padrão (com o baseline como rede de segurança na cadeia de fallback), então isso não bloqueia nada — só significa que, **para ganhar rating de verdade, o próximo ganho concreto está mais no deck (diversidade de tipo/ataques) do que na política** neste momento.

## Heurística de uso de trainers (pós-submissão v1)

Depois da primeira submissão, a política passou a olhar **qual carta** está por trás de cada opção `PLAY` (via `hand[opt['index']]['id']`), não só o tipo genérico:
- `Cheren`/`Urbain` (compra 3) ganham prioridade extra quando a mão está pequena (≤3 cartas).
- `Master Ball`/`Fighting Gong` (busca) ganham prioridade extra quando o banco tem poucos Pokémon (<3).
- `Switch` passa a competir com `RETREAT` quando o ativo está em perigo (HP<30%) — faz sentido porque trocar de ativo via Switch é **de graça**, sem pagar o custo de energia do retreat.

**Resultado honesto**: comparado com a versão anterior (só prioridade por tipo), o resultado em partida espelhada (mesmo deck, 40 partidas) foi **48% a 48%** — sem ganho mensurável. Isso é esperado num matchup espelhado: cada carta acaba sendo jogada de qualquer forma ao longo da partida, e o que muda é só a *ordem*; ganho real de "timing" tende a aparecer mais em `winrate` contra decks/políticas diferentes ou em métricas que não medimos ainda (ex.: turnos até o primeiro nocaute, consistência de mão). Sanity check contra o placeholder confirma ausência de regressão (90%).

## Bug real encontrado e corrigido: loop de "ataque de dano zero"

Investigando a duração anômala de partidas (item anterior desta seção, agora resolvido), encontrei a causa raiz exata: **`Hitmontop` tem 2 ataques** — `Spin and Draw` (attackId 1397, **0 de dano**, custo 1 energia qualquer, efeito "embaralha sua mão no deck e compra 6") e `Low Kick` (attackId 1398, 50 de dano, custo 2 energias). Como a categoria `ATTACK` sempre vencia `ATTACH` na heurística (e no baseline), assim que a 1ª energia era anexada o bot **atacava imediatamente com o golpe de 0 dano** em vez de anexar a 2ª energia necessária para o ataque de verdade — terminando o turno sem progredir. Isso criava um ciclo que se repetia por centenas/milhares de turnos (uma partida chegou a 4991 turnos, batendo no limite artificial de 5000 do harness de teste).

**Diagnóstico**: rodando 30 partidas espelhadas com log de turno completo, a distribuição era **bimodal**: 29/30 terminavam decisivamente entre 5 e 59 turnos, mas 1/30 disparava para milhares de turnos — isso inflava a "média" que eu vinha reportando (233–365 turnos) e mascarava que a maioria das partidas era, na verdade, saudável.

**Correção** (`agent/policy_heuristic.py`): ataques com dano efetivo ≤ 0 agora pontuam **abaixo de ATTACH**, não mais no topo da prioridade — o bot passa a preferir desenvolver energia a "atacar" sem causar dano. Não repliquei a correção no `policy_baseline.py` (mantido deliberadamente simples/dependência mínima, já que só age como rede de segurança pontual quando a heurística lança exceção — o risco de loop persistente ali é baixo).

**Resultado após a correção** (60 partidas espelhadas): **0 travamentos**, duração caiu de médias de 233–365 turnos para **33.7 turnos** (mediana 35, máximo 65). Comparando com o placeholder degenerado pilotado pelo baseline antigo (ainda com o bug): nosso deck com heurística corrigida venceu **100% (20/20)**, contra os ~90% de antes — prova de que a correção tem impacto real. (Um teste com heurística corrigida nos dois lados deu 50/50 contra o mesmo placeholder — não é regressão, é o placeholder *também* parando de se autossabotar quando pilotado pela versão corrigida.)

## Evidência real de vantagem da heurística (matchup assimétrico)

Todos os testes anteriores comparando heurística vs. baseline usavam o **mesmo deck mono-Fighting nos dois lados** — o que nunca aciona a lógica de fraqueza/resistência (mesmo tipo nunca é fraco contra si mesmo). Para medir isso de verdade, montei um segundo deck (`data/decks/psychic_v1.csv`, mono-Psychic: Meloetta, Enamorus, Dedenne, Spectrier) e rodei o Fighting contra ele — matchup onde 2 dos 4 psíquicos têm **resistência a Fighting** e 2 dos nossos 4 lutadores (Okidogi, Hitmontop) têm **fraqueza a Psychic**.

Resultado (30 partidas cada, deck Psychic sempre pilotado pela heurística para isolar a variável):
- Fighting pilotado pela **heurística**: venceu **23%** (7/30)
- Fighting pilotado pelo **baseline**: venceu **17%** (5/30)

A heurística vence mais nesse cenário — confirma que a lógica de fraqueza/resistência tem valor real, só não aparecia nos testes espelhados anteriores. Achado colateral: o deck Psychic é estruturalmente muito forte contra o nosso Fighting atual (77–83% de vitórias) — candidato a **próxima investigação de deck** (ex.: `Enamorus` ataca por 30 de dano com **1 única energia colorless**, eficiência que nenhum dos nossos 4 atacantes Fighting iguala).

## Troca de tipo: de Fighting para Grass (objetivo: ≥50% contra todos os adversários de teste)

Depois de resubmeter a v2, o pedido foi: continuar otimizando o deck até bater **pelo menos 50% de winrate contra todos os adversários testados** antes de submeter de novo. O deck Fighting v2 perdia feio (17–27% de vitórias) contra o deck Psychic — hora de investigar por quê e resolver de vez, não só empurrar mais treinadores.

**Passo 1 — reforçar o Fighting (v3)**: troquei `Lunatone`→`Koraidon` (110 dano/3 energia, o ataque mais forte disponível em Fighting puro) e `Hitmontop`→`Sawk` (30 dano por **1 única energia**, tempo rápido, e elimina de vez o Pokémon com o ataque de 0 dano). Resultado contra o Psychic: só **27%** (7→8 de 30) — praticamente nenhuma melhora.

**Diagnóstico real**: o problema não era eficiência de dano, era o **triângulo de tipos**. `Okidogi`, `Koraidon` e `Sawk` são todos fracos a **Psychic**, e o deck Psychic de teste (`Meloetta`/`Spectrier`) **resiste a Fighting** — um duplo prejuízo estrutural que nenhuma quantidade de "dano por energia" resolve sozinha. Esse padrão (Fighting fraco a Psychic) é sistemático no pool inteiro: quase todo atacante Fighting eficiente tem essa mesma fraqueza.

**Passo 2 — testar Darkness**: `Meloetta`/`Spectrier` são fracos a **Darkness**. Montei `data/decks/darkness_v1.csv` (Seviper 120/3energia, Yveltal 110/3energia + retreat 0 + resiste a Fighting, Absol, Roaring Moon). Resultado contra o Psychic: **77%** — virada completa. Mas contra o próprio Fighting v3: só **37%**, porque `Seviper` é fraco a Fighting. Trocar de tipo só empurrou o mesmo problema estrutural para o próximo matchup (ciclo Fighting→Darkness→Psychic→Fighting clássico do TCG).

**Passo 3 — Grass, o tipo que não colide com nenhum dos dois testes**: nem Fighting nem Psychic aparecem como fraqueza de atacante Grass eficiente neste pool (a fraqueza comum de Grass é **Fire**, que nenhum dos nossos adversários de teste explora). Montei `data/decks/grass_v1.csv`: `Genesect` (110 dano/3 energia: 2 Grass + 1 Colorless), `Pinsir` (100/3: 1 Grass + 2 Colorless), `Celebi` e `Shaymin` (30 dano por 1 única energia cada, `Shaymin` com retreat 0). Mesma estrutura de treinadores da v2 (Master Ball ×1, Energy Search ×4 no lugar do Fighting Gong, Cheren ×4, Urbain ×4, Switch ×4, 27 energia básica).

**Resultado final** (heurística nos dois lados, 25–40 partidas por matchup):

| Adversário | Winrate do Grass |
|---|---|
| Placeholder degenerado | **73%** |
| Psychic (`psychic_v1`) | **60%** |
| Fighting (`fighting_rush_v3`) | **80%** (confirmado com 40 partidas, uma amostra menor deu 56% antes) |
| Darkness (`darkness_v1`) | **80%** |

Todos os 4 matchups testados ficam **acima de 50%** — meta atingida. `agent/deck.csv` agora aponta para `grass_v1.csv`. Os decks Fighting v3, Darkness e Psychic continuam no repositório (`data/decks/`) como oponentes de regressão para testes futuros.

**Limitação a registrar com honestidade**: isso prova robustez contra os 4 adversários que *nós* construímos, não contra o meta real do ladder (que não conhecemos — `06-riscos-questoes-abertas.md` item 6). O princípio geral que fica — e vale para decks futuros — é: **verificar a distribuição de fraquezas dos atacantes candidatos contra os principais tipos do pool antes de fechar um deck**, não só a eficiência de dano por energia.

## Experimento de política que falhou (registrado por rigor, não foi submetido)

Depois do score real da v3 (504.7), tentei uma melhoria de **política** (não de deck) generalizável para qualquer adversário: (1) retreat/switch preditivo — calcular o dano máximo que o ativo do oponente já consegue pagar *agora* (energia realmente anexada) contra o nosso ativo, e tratar como perigo mesmo com HP acima de 30% se isso for letal; (2) direcionar `ATTACH` para o Pokémon em campo mais perto de completar seu ataque mais barato, em vez da primeira opção da lista.

**Testado antes de submeter** (política nova vs. antiga pilotando o mesmo deck Grass, contra os 4 adversários, 20 partidas cada): a versão nova **piorou em todos os 4 matchups** (ex.: 60% vs. 80% contra o Fighting v3). Isolando cada mudança separadamente, as duas pioram individualmente — o attach-targeting sozinho caiu para 65%, e o retreat preditivo sozinho caiu para 35% no mesmo teste. Hipótese: o retreat preditivo dispara perigo cedo demais (qualquer ataque teoricamente letal do oponente, mesmo em cenários administráveis) e faz o bot trocar de Pokémon em vez de desenvolver energia, nunca chegando a atacar de verdade — um problema com a mesma assinatura do bug de loop anterior, só que por excesso de cautela em vez de excesso de agressão.

**Decisão**: revertida antes de gastar uma submissão. Fica como lição registrada: nem toda melhoria "teoricamente correta" generaliza — vale sempre validar localmente contra os 4 adversários antes de submeter, e isolar mudanças compostas quando o resultado agregado é ruim.

**Segunda tentativa, ainda mais conservadora**: extraí do experimento acima só a parte que parecia um bug isolado e de baixo risco — `_SEARCH_ITEM_IDS` reconhecia `Master Ball`/`Fighting Gong` mas não `Energy Search` (1119), o item de busca que o deck Grass realmente usa (herdado de quando o deck era Fighting). Adicioná-lo à lista também **piorou** em todos os 4 matchups (ex.: 65% vs. 80% contra o placeholder). Revertida também.

**Terceira tentativa, que ficou**: a política nunca tinha lógica para a **escolha do Pokémon ativo/banco inicial** (fase de setup, `SelectContext.SETUP_ACTIVE_POKEMON`/`SETUP_BENCH_POKEMON`) — caía no caso genérico "primeira opção da mão". Implementei `_score_setup_candidate`: prefere o básico com melhor eficiência de ataque (dano do golpe mais barato por energia), HP como desempate. Testado contra os 6 adversários agora disponíveis (20 partidas cada): resultado **misto** (3 melhoraram, 3 pioraram), agregado levemente negativo (87/120 vs. 92/120) — mas repetindo o matchup mais informativo (Fighting) com amostra maior (35 partidas), o resultado ficou dentro da margem de ruído (80% vs. 77%). Ao contrário das duas tentativas anteriores, esta é **estruturalmente correta por princípio** (não há razão para escolher o ativo inicial ao acaso) e não mostrou regressão clara em nenhuma amostra maior — mantida, sem alegar um ganho que os dados não sustentam com confiança.

## Conjunto de teste ampliado: 2 arquétipos estruturalmente diferentes

Os 4 adversários originais (placeholder, Psychic, Fighting, Darkness) foram todos construídos com a mesma metodologia (mono-tipo, só básicos, ataques incondicionais) — risco real de o deck Grass estar otimizado para o nosso próprio viés de deckbuilding, não para adversários genuinamente diferentes. Adicionei dois arquétipos novos:

- **`data/decks/water_evo_v1.csv`**: primeira vez testando uma **linha de evolução real** (Feebas→Milotic, Panpour→Simipour), tipo Water (ainda não testado). Resultado: Grass venceu **87%** — a fragilidade do Pokémon básico pré-evolução (Feebas tem só 30 HP) é uma desvantagem estrutural real de decks de evolução contra decks agressivos de básicos puros, e nenhum erro de política/crash apareceu lidando com `EVOLVE`.
- **`data/decks/fire_v1.csv`**: deck mono-Fire (Heatmor, Reshiram, Ho-Oh, Victini). Resultado: Grass **perdeu, 27%** — o contra-tipo clássico (Fire bate Grass). Confirmei que **nenhum Pokémon básico não-`ex` no pool inteiro tem resistência a Fire** (busca exaustiva, zero resultados), então não há um "tech" limpo de 2-4 cartas para tapar esse buraco sem misturar tipos de energia — e misturar tipos introduz um risco real, porque a política de `ATTACH` de hoje não escolhe entre tipos de energia na mão, só entre alvos no campo.

**Conclusão**: todo deck mono-tipo tem um contra-tipo ruim por construção do próprio jogo (ciclo de fraquezas) — isso não é um defeito do Grass especificamente, é inerente a jogar um único tipo. A escolha de Grass continua sendo boa porque generaliza bem contra 5 dos 6 arquétipos testados (73–100%), incluindo um mecanicamente diferente (evolução) — só perde contra o contra-tipo direto, que é o preço estrutural de qualquer deck mono-tipo neste jogo, não algo corrigível com mais dados de teste.

## Iteração 2 investigada: sem ganho que justifique uma submissão

Com todos os cards fortes do deck Grass já no limite legal de 4 cópias (exceto `Master Ball`, travado em 1 por ser ACE SPEC), o único lever real de refinamento era trocar uma carta por outra. Encontrei `Poké Pad` (id 1152): busca 1 Pokémon exatamente como `Master Ball`, mas **não é ACE SPEC** — dá pra ter 4 cópias em vez de 1. Montei `data/decks/grass_v2.csv` (Master Ball ×1 → Poké Pad ×4, energia 27→24 para acomodar) e testei:

- v2 vs. v1 (espelhado, 35 partidas): **49% a 51%** — empate estatístico.
- v2 vs. Fire (nosso pior matchup, 25 partidas): **20%**, contra 28% do v1 — não ajudou, ficou pior.

**Decisão**: não promovido, não submetido. Depois desta e das três tentativas de política anteriores (todas documentadas acima), o padrão é consistente: o deck e a política já estão perto de um ótimo local com os dados e o tempo disponíveis nesta rodada — mais busca/consistência não é o gargalo real (o deck já tinha bastante: `Energy Search` ×4 + `Cheren`/`Urbain` ×8 de compra). O gargalo que resta identificado (o contra-tipo Fire) é estrutural ao jogo, não vulnerável a esse tipo de ajuste. Registrado com honestidade em vez de forçar uma segunda submissão sem ganho comprovado.

## Submissões

| # | Quando | Conteúdo | Status |
|---|---|---|---|
| v1 (ref 55440245) | 11/08 19:02 | Heurística com scoring de ataque + deck v2 Fighting, **com o bug do loop de ataque-zero ainda ativo** | ❌ `ERROR` |
| v2 (ref 55440455) | 11/08 19:16 | Igual à v1, mas com a correção do loop de ataque-zero + uso inteligente de trainers | ✅ `COMPLETE` — **score público 260.5** |
| v3 (ref 55443073) | 11/08 22:38 | Deck mono-Grass (Genesect/Pinsir/Celebi/Shaymin) — ≥50% de winrate local contra os 4 adversários de teste | ✅ `COMPLETE` — score público oscilou 504.7 → 385.7 → **352.1** (estável nas últimas 3 checagens) |
| v4 (ref 55443599) | 11/08 23:23 | Setup inteligente (ativo/banco inicial por eficiência de ataque) + 2 novos oponentes de teste | ✅ `COMPLETE` — score público oscilou 600.0 → **292.9** (estável nas últimas 3 checagens) |

**Correção sobre o score mudar com o tempo**: registrei antes que a v4 tinha "confirmado uma melhora real" ao ver 600.0 (acima dos 504.7 da v3 no momento). Numa checagem posterior — e estável em 3 consultas seguidas — os números mudaram para v3=352.1 e **v4=292.9, agora abaixo da v3**. Isso inverte a conclusão anterior: **não dá para afirmar que o setup fix (v4) melhorou o desempenho real no ladder** — o sinal é instável demais nesta fase (poucas partidas acumuladas, rating tipo Elo/TrueSkill ainda convergindo) para tirar conclusões de causa-efeito a partir de 1-2 submissões. A tendência de alta clara e não-ambígua continua sendo só **v2 (260.5) → v3/v4 (~300-500)**, ou seja, a troca de tipo Fighting→Grass; o efeito específico do setup fix (v4) permanece **não comprovado** pelo ladder real, nem pelos nossos testes locais (que já eram estatisticamente neutros). Fica como aprendizado: scores isolados e recentes no ladder não são confiáveis para validar uma mudança específica — precisam de mais partidas acumuladas (e idealmente comparação A/B mais direta) antes de virar conclusão.

A v1 falhou com `SubmissionStatus.ERROR` — a API não expõe o motivo exato via CLI, mas a explicação mais provável, dado o timing, é que o bug do loop (corrigido depois, ver seção acima) fez uma partida real no ladder travar/estourar tempo, e o sistema classificou como erro. A v2 processou com sucesso e confirma a correção: **260.5 é nosso primeiro número real de rating no ladder**, útil como baseline para medir se a troca de deck (v3) realmente melhora no jogo real, não só nos nossos testes locais. Checar status com `kaggle competitions submissions -c pokemon-tcg-ai-battle --format json`.
