# 12 · Imitation learning (13/08/2026) — primeira tentativa, resultado negativo mas informativo

## Contexto

O usuário pediu para investigar se uma abordagem de rede neural faria sentido, dado que a otimização por ajuste manual de heurística havia atingido retornos decrescentes (`docs/11`, iterações 11-13). Depois de confirmar viabilidade (ver seção abaixo), o usuário pediu explicitamente para seguir com imitation learning e "comprar esse risco".

## Viabilidade confirmada antes de investir tempo

1. **Dependências em runtime**: `kaggle-environments` (o pacote que roda a competição) lista `numpy`, `jax` e `transformers` como dependências diretas (`pyproject.toml` do repositório oficial) — forte indício de que essas bibliotecas estão disponíveis no ambiente de execução dos agentes (mesma imagem Docker, segundo a FAQ oficial). Mas para **eliminar esse risco por completo**, a decisão de design foi: treinar offline com numpy/scikit-learn (instalados neste ambiente de desenvolvimento via `pip install`, sem problema de rede), e depois **extrair os pesos treinados como constantes e reimplementar a inferência em Python puro** — o agente final não importa nenhuma biblioteca externa, então a pergunta "o runtime tem numpy?" deixa de importar.
2. **Dados de treino**: já tínhamos ~275 episódios reais do ladder baixados (`docs/09`, `docs/11`), suficientes para uma primeira tentativa.

## Pipeline construído

- `scripts/build_imitation_dataset.py`: replay dos episódios, extraindo pares (features de cada opção de um MAIN select de escolha única, índice escolhido) — só de decisões tomadas por jogadores que **venceram** a partida (imita vencedores, não qualquer jogada). Confirmação da estrutura dos dados: `steps[i][jogador].observation.select` é o select mostrado, e `steps[i+1][jogador].action` é a resposta dada a ele (formato padrão `kaggle_environments`).
  - 275 episódios → 12.088 decisões de vencedores → 210.024 pares de treino (formulação pairwise: para cada decisão, `features[escolhido] - features[outro]` com rótulo 1, e o inverso com rótulo 0 — assim uma regressão logística aprende uma função linear de pontuação onde a opção escolhida pontua mais alto que as alternativas).
  - Features (20 no total): one-hot do tipo de opção (ATTACK/EVOLVE/ABILITY/DISCARD/PLAY/ATTACH/RETREAT/END) + específicas por tipo (dano normalizado, dano relativo ao HP do defensor, é letal, é dano zero, alvo é ativo/banco, tipo de energia bate, é Supporter/Item/Stadium, ativo em perigo).
- `scripts/train_imitation.py`: regressão logística (scikit-learn) nos pares, imprime os pesos.
- `agent/policy_ml.py`: reimplementação em Python puro (sem numpy/sklearn) da mesma extração de features + produto escalar com os pesos treinados — usa exatamente a mesma interface `choose(obs)` das outras políticas, plugável na cadeia de fallback.

## Resultado do treino

Acurácia por pares: **~74%** (treino e teste, sem overfitting aparente — 210k exemplos, modelo simples). Bem acima do acaso (50%), mas moderado — um modelo linear com features grosseiras não captura interações complexas de contexto (ver limitação abaixo).

**Achado curioso nos pesos**: o coeficiente de "ataque de dano zero" saiu fortemente **positivo** (+1.37) — a princípio alarmante, porque contraria o próprio fix que corrigimos bem no início desta sessão (o bug do loop do Hitmontop/Genesect, `docs/08`). Investigando: isso reflete o dataset genérico ter muitos ataques de utilidade (busca, cura, troca) que jogadores bons usam com frequência e corretamente — mas no **nosso deck especificamente**, isso inclui os primeiros ataques de `Genesect`/`Pinsir`, que sabemos ser arriscados sem critério adicional. Também descobri, investigando isso, que o ataque "Bug's Cannon" do `Genesect` (`damage=0` no campo bruto) na verdade **escala com energia anexada** ("does 20 damage... for each {G} Energy attached") — nem a heurística nem o modelo de ML capturam esse tipo de escala (só leem o campo `damage`, não o texto do efeito) — um paralelo direto ao achado do Ogerpon na iteração 8 do loop, só que a nosso favor dessa vez (potencial não aproveitado). Ajustei manualmente o peso desse índice para um valor conservador (-0.5, alinhado com a heurística) em vez de confiar cegamente no valor aprendido, dado que temos evidência forte e específica de que é arriscado para o nosso deck.

## Validação empírica — metodologia importa (de novo)

**Teste 1 (espelho, mesmo deck dos dois lados)**: `policy_ml` vs `policy_heuristic` pilotando o **mesmo** deck nosso um contra o outro — `policy_ml` venceu **62%** (n=60). Resultado animador à primeira vista.

**Teste 2 (metodologia correta, igual à usada a sessão inteira)**: nosso deck pilotado por `policy_ml` contra os arquétipos reais, com o **oponente pilotado por `policy_heuristic`** (o proxy padrão usado em toda validação desta sessão, para isolar o efeito de mudar SÓ a nossa política):

| Adversário | Winrate `policy_heuristic` (baseline) | Winrate `policy_ml` |
|---|---|---|
| `munkidori_impidimp` | 72-77% | 62% (n=40) |
| `dreepy_dragapult` | 85-96% | 68% (n=40) |
| `dwebble_crustle_kangaskhan` | 13-35% | 18% (n=40) |
| `ogerpon_solo` | 8-13% | 5% (n=40) |

**Resolução da aparente contradição**: o teste 1 mede "quem pilota melhor o MESMO deck contra o próprio espelho" — não é a pergunta que importa. A pergunta que importa é "nosso deck com essa política vence mais contra o campo real?", e para isso o oponente precisa ser pilotado por uma política **fixa e conhecida** (nosso proxy padrão), não pela mesma política sendo avaliada dos dois lados. Com a metodologia certa, `policy_ml` fica **em pé de igualdade ou abaixo** de `policy_heuristic` em todos os matchups testados — às vezes por uma margem grande (`dreepy`: 68% vs 85-96%).

## Decisão

**Não promovido.** Esta primeira versão de imitation learning, mesmo com o ajuste manual do peso problemático, não supera a heurística extensivamente ajustada nesta sessão — na verdade fica pior nos matchups onde a heurística já era forte. Isso não invalida a abordagem (74% de acurácia por pares mostra sinal real, e o modelo aprendeu preferências sensatas como priorizar `EVOLVE`/`ABILITY`, dano letal, e recuo em perigo), mas confirma que um modelo linear simples com features grosseiras, treinado em dados genéricos de todo o campo, não bate uma heurística **especificamente calibrada** para o nosso deck e nossos adversários catalogados depois de uma sessão inteira de iteração.

**Infraestrutura mantida no repositório** (`agent/policy_ml.py`, `scripts/build_imitation_dataset.py`, `scripts/train_imitation.py`) como base para uma tentativa futura mais robusta, caso valha a pena investir mais tempo — não integrado à cadeia de produção (`agent/main.py` continua só com `policy_heuristic`→`policy_baseline`→`safe_selection`).

## Caminhos para uma segunda tentativa, se o usuário quiser continuar investindo nisso

1. **Mais features de contexto com termos de interação** — features puramente de contexto (turno, HP, tamanho da mão) não sobrevivem à formulação pairwise atual (a diferença entre duas opções da MESMA decisão anula qualquer feature que não varie por opção) — precisariam ser combinadas via produto com features específicas da opção (ex.: `dano_relativo × (1 - seu_hp_ratio)`), ou trocar para um modelo não-linear (MLP pequeno) que combine contexto+opção livremente.
2. **Mais dados**: 275 episódios é uma amostra pequena para um problema desse tamanho — mais dias de dataset (`kaggle/pokemon-tcg-ai-battle-episodes-YYYY-MM-DD`) ajudariam.
3. **Filtrar/pesar por qualidade real**: hoje "vencedor" é o único filtro de qualidade — poderia pesar por margem de vitória, ou por rating do jogador se essa informação existir em algum dataset agregado.
4. **Blend em vez de substituição**: em vez de trocar a heurística pelo modelo, usar o modelo só para os tipos de decisão onde ele mostrou mais sinal (ex.: `EVOLVE`/`ABILITY`/`RETREAT`), mantendo a heurística fina para `ATTACK`/`ATTACH` onde ela já é muito bem calibrada.
