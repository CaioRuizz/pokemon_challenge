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
