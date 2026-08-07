# 06 · Riscos e Questões Abertas

## 1. ~~Sem acesso oficial aos dados/regras da competição~~ — RESOLVIDO em 07/08/2026

Após o usuário aceitar as regras das duas competições e fornecer um token da API do Kaggle, baixamos os arquivos oficiais de `pokemon-tcg-ai-battle` via `kaggle competitions download`: o `sample_submission/` completo (`main.py`, `deck.csv`, `cg/` com o engine nativo), o source C++ do engine (`ptcg_engine/`) e as bases de cartas (`EN/JP Card Data.csv`). `01-definicao-problema.md` foi reescrito com esses dados reais.

**Ainda falta ler**: a aba `/rules` da competição em si (texto jurídico/regras de scoring), que não vem nos arquivos de dados — ver item 6 abaixo.

**Nota operacional**: as credenciais da API do Kaggle usadas para isso ficaram salvas em `~/.kaggle/` neste container remoto (efêmero). Se este ambiente for reaproveitado por outra tarefa, considere revogar/regerar o token nas configurações do Kaggle.

## 2. ~~Datas de deadline não confirmadas~~ — RESOLVIDO

Confirmado via `kaggle competitions list` (dado estruturado da própria API, não imprensa): Simulation encerra **16/08/2026 23:59**, Strategy encerra **13/09/2026 23:59**, prêmio Strategy = **US$ 240.000**. Bate com a estimativa mais conservadora que já estava no roadmap.

## 3. Licenciamento de assets — RESOLVIDO (regra confirmada, ação pendente)

Confirmado: o engine (`ptcg_engine/`, `cg/`) tem licença **`LicenseRef-PTCG-ABC-Competition-Use-Only`** — uso restrito à competição, proibida redistribuição/publicação, apagar ao final. Isso vale também para os dados de carta em PDF/CSV oficiais (mesmo pacote, mesma licença implícita de "Pokémon Elements").

**Regra prática para este repo** (já refletida em `03-arquitetura.md`): nunca dar `git add` em nada baixado de dentro de `sample_submission/`, `ptcg_engine/`, `*.pdf`, `*Card Data.csv`. Esses arquivos ficam só localmente (`vendor/`, gitignorado) e são recriados via `scripts/fetch_official.sh` sempre que necessário. Só código nosso (política, harness de avaliação, deck escolhido) é versionado.

## 4. Sistema de rating do ladder — ainda não confirmado

Os arquivos técnicos baixados (engine, `cg/api.py`) não descrevem como o ladder pontua as partidas (Elo puro? TrueSkill μ/σ?). Fontes de terceiros divergem entre si nesse ponto. Precisa vir do `/rules` ou da aba de leaderboard/discussão oficial — não é bloqueante para começar a codar (o agente não decide baseado nisso), mas afeta como lemos nosso próprio progresso no ladder.

## 5. Limite de tempo por jogada — ainda não confirmado

Fontes de terceiros mencionam um limite de tempo por decisão do agente, mas isso não apareceu nos arquivos técnicos lidos até agora (nem em `cg/api.py`, nem no `README.md` do engine). Relevante para decidir o quão "cara" a Fase 3 (busca via `search_begin`/`search_step`) pode ser em produção. Precisa ser confirmado no `/rules` antes de investir tempo em busca profunda.

## 6. Regras oficiais completas (`/rules`) ainda não lidas

Só baixamos **dados** (engine, cartas, sample_submission) via API — o texto de regras em si (`https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/rules`) é uma página só de texto/HTML, não um "arquivo de dados" baixável pela API `competitions files`/`download`. Precisa ser lido manualmente (copiar/colar aqui, ou por outro meio) para confirmar: banlist/regras de deck além do que já vimos nos dataclasses (ex.: 1 ACE SPEC), regras de scoring do ladder (item 4), limite de tempo (item 5), e critérios de avaliação da trilha Strategy (o que faz um relatório competitivo).

## 7. Risco de cronograma

A trilha Simulation fecha em **16/08/2026** (confirmado, item 2) — a partir de hoje (07/08) restam ~9 dias. Com o contrato técnico já validado (item 1), o próximo risco é gastar tempo demais em pesquisa e pouco em ter uma submissão válida rodando cedo. Mitigação: seguir a ordem de fases do `02-estrategia-solucao.md` — baseline "nunca crasha" primeiro, otimização depois.
