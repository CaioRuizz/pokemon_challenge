# 10 · Fine-tuning avançado (12/08/2026) — definição de "satisfatório" e plano

## Contexto crítico (por que isso muda a abordagem)

- **Prazo real**: trilha Simulation fecha **16/08/2026 23:59 UTC**. Nesta data (12/08, ~03:20 UTC), restam **~4 dias e 20 horas**.
- **Posição real no ladder**: `userRank: 5816` de **6757 times** (consultado via `kaggle competitions list`). Não é uma posição de meio de tabela — estamos na faixa de baixo.
- **Distribuição real de score** (leaderboard + `data/meta/episodes_manifest.csv`, coluna `median_avg_score` dos últimos dias): topo em **1100–1300**, mediana do campo em **~1020–1030**. Nossos scores até agora oscilaram entre **260 e 600** (instáveis — o rating parece ainda estar convergindo, poucas partidas acumuladas por submissão).
- **Leitura honesta**: o topo do leaderboard provavelmente usa busca (MCTS) ou aprendizado por reforço, não só heurística de regras fixas como a nossa. Fechar 100% da diferença para o topo em 4 dias com o approach atual não é realista. A meta desta rodada é **progresso real e mensurável**, não o topo do ranking.

## Definição de "resultado satisfatório" (critérios de saída — só submeter quando bater isto)

1. **Winrate local ponderado pelo uso real do meta ≥ 80%** (linha de base atual: 73.7%, ver `docs/09`). Calculado contra os arquétipos reais extraídos do ladder (`data/decks/real_*.csv`), ponderado pela % de uso observada.
2. **Nenhum arquétipo com ≥10% de uso do campo abaixo de 30% de winrate.** Hoje o `Teal Mask Ogerpon ex` (12.8% de uso) está em 10% — viola este critério.
3. **Robustez**: 0 crashes / 0 seleções ilegais em qualquer teste; duração de partida dentro de limites seguros (sem sinal de loop/timeout) em amostras de 30+ jogos contra todos os adversários catalogados.
4. **Margem de segurança de prazo**: ter uma versão final pronta e submetida com pelo menos 1 dia de folga antes do fechamento (ou seja, até 15/08), não na última hora.
5. **Meta secundária, não bloqueante**: score real no ladder acima de 700 de forma consistente (múltiplas submissões, não um pico isolado) — não é critério de bloqueio (o rating tem ruído e depende do campo, não só de nós), mas é o sinal de "progresso real" que buscamos.

Se o tempo se esgotar antes de bater todos os critérios acima, o desempate é: **submeter a melhor versão validada localmente antes de arriscar ficar sem tempo** — uma submissão real feita com segurança vale mais que otimização incompleta não enviada.

## Plano de trabalho desta rodada

1. Expandir a base de adversários reais (mais arquétipos, sub-variantes, amostra mais recente/maior do ladder).
2. Iterar em deck: testar variações mais amplas guiadas pelos dados reais (não só type-matching, também eficiência geral, curva de energia, escolha de trainers).
3. Iterar em política: continuar do ponto onde paramos (`docs/09`), com validação rigorosa (30+ partidas, nunca prometer ganho sem confirmar).
4. Analisar aspectos além do deck/política: ler as regras oficiais (`/rules`, ainda pendente desde `docs/06`), confirmar limite de tempo por jogada, revisar `agent/fallback.py` e a cadeia de fallback para garantir robustez sob pressão de tempo real.
5. Só empacotar/submeter quando os critérios acima forem atingidos ou o prazo apertar de verdade (ver critério de desempate).

Cada iteração desta rodada é registrada abaixo, seguindo a convenção do `CLAUDE.md`.

## Status ao final desta rodada (12/08) — ver detalhes completos em `docs/09`

Resumo executivo (log completo, com todos os experimentos, tabelas e números, em `docs/09-meta-real-do-ladder.md`, seções "Fine-tuning avançado"):

- **Regras oficiais lidas por completo** (`docs/06`, itens 4-6 fechados): rating é TrueSkill com μ0=600; limite de tempo por jogada permanece **não documentado** em nenhuma fonte oficial acessível (mitigado com medição própria: latência máx. 38ms, bem abaixo de qualquer limite plausível); prêmio em dinheiro está de fato atrelado à trilha Strategy/Hackathon, não à Simulation em si.
- **Base de adversários reais expandida**: de 4 para 9 arquétipos, cobrindo 82.9% de uma amostra fresca de 398 decks (199 episódios de 10-11/08), com winrate ponderado pelo uso real como métrica principal.
- **Achado crítico**: o baseline real (medido contra a amostra nova e mais representativa) é **59.8%**, não os 73.7% medidos na rodada anterior contra uma amostra menor e favorável por acaso.
- **Deck iterado com rigor**: 4 variantes testadas (`v4`, `v5`, `v6`, `v8`), uma descoberta importante (armadilha das 2 prize cards de Pokémon `ex` — `v4` revertida), uma promovida (`v5`: Celebi→Virizion, 68.2% ponderado, sem regressão em nenhum dos 9 arquétipos reais nem nos 5 sintéticos).
- **Política**: nenhuma mudança nova de alto risco tentada nesta rodada — o "retreat preditivo" já tinha falhado 2x antes (`docs/08`); decisão consciente de não tentar uma 3ª vez sem uma técnica estruturalmente diferente (busca/lookahead).
- **Robustez auditada**: `agent/fallback.py` e a cadeia de 3 camadas revisadas, sem bugs encontrados; 0 erros em 700+ partidas locais.
- **Critérios de "satisfatório" (seção acima)**: 1 (≥80% ponderado) e 2 (nenhum arquétipo ≥10% <30%) **não atingidos**; 3 (robustez) e 4 (margem de prazo) **atingidos**; 5 (score real >700) ainda sem dado novo.
- **Decisão**: submetida a `v7` (deck `grass_v5` + política já existente) mesmo sem bater 100% dos critérios — é uma melhoria real e validada (+8.4pp ponderado, zero regressão), submissões são baratas (restam 2 hoje), e os dois problemas remanescentes (famílias Ogerpon ~11.8% e Kangaskhan ~10.1% de uso) são estruturais ao pool de cartas Grass + à falta de busca, não corrigíveis por mais uma iteração incremental de heurística. Ficam registrados como o trabalho real da próxima rodada: (a) considerar um deck multi-tipo tech'ado especificamente contra Kangaskhan (fraco a Fighting), ou (b) investir na API nativa `search_begin`/`search_step` para lookahead de verdade.
