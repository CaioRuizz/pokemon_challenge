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

## 4. Sistema de rating do ladder — RESOLVIDO em 12/08/2026

Lido via `kaggle competitions pages -c pokemon-tcg-ai-battle --content --page-name Evaluation`: o ladder usa um sistema estilo **TrueSkill** (rating N(μ, σ²)), com **μ0 = 600** como valor inicial de todo agente novo. σ diminui (rating fica mais "confiante"/estável) conforme mais episódios são jogados. Isso muda a leitura dos nossos scores observados (260–600): a maior parte está **abaixo** do ponto neutro de partida, não "baixo mas subindo de zero" — ver `docs/10-fine-tuning-avancado.md`. A "Validation Episode" (partida contra si mesmo) roda antes de o agente entrar no pool de matchmaking real.

## 5. Limite de tempo por jogada — CONFIRMADO COMO NÃO DOCUMENTADO (12/08/2026)

Busca extensiva não encontrou nenhum limite de tempo por jogada/turno/episódio documentado publicamente:
- `rules.txt` (44 KB, texto completo de `/rules`): zero ocorrências de "time limit", "timeout", "seconds", palavras relacionadas.
- Página FAQ oficial: menciona "Submission Resources" (`AgentDisk`, `AgentRam`, `AgentCpuCores`, `SubmissionSizeLimit`) mas como variáveis de template do Kaggle (`${competition.AgentDisk}`) — não resolvidas pela API nem pelo HTML estático da página (SPA renderizada em JS; o HTML bruto é só o shell de carregamento, ~5.7 KB).
- Documentação externa do engine (`https://matsuoinstitute.github.io/cabt/` — `api.html`, `game.html`, `sim.html`, referenciada pela página oficial "How to Play"): nenhuma menção a timeout/limite de tempo/CPU/memória em nenhuma das três páginas.
- Thread de discussão oficial da competição (tópico 708586, 28 mensagens, lida por completo via `kaggle competitions topic-messages`): nenhuma pergunta ou resposta sobre limite de tempo.

**Conclusão prática**: não há como confirmar um número exato antes do prazo. Mitigação adotada (em vez de continuar buscando): tratar como **risco desconhecido mas plausivelmente real** — evitar qualquer política que faça buscas custosas (ex.: MCTS profundo via `search_begin`/`search_step`) sem medir o tempo de execução localmente primeiro, e manter a heurística atual (O(nº de opções), sem laços não determinísticos) como está — já é seguramente rápida. Ver auditoria de robustez em `docs/10-fine-tuning-avancado.md` (item 3 dos critérios de "satisfatório").

## 6. Regras oficiais completas (`/rules`) — RESOLVIDO em 12/08/2026

Lidas por completo via `kaggle competitions pages -c pokemon-tcg-ai-battle --content --page-name <X>` (contorna o problema de SPA em JS que bloqueava a leitura direta da página desde o início do projeto). Páginas lidas: `rules`, `Evaluation`, `Description`, `FrequentlyAskedQuestions`, `How_to_Submit_to_this_Competition`, `HowtoPlayPokémonTCG`, `Timeline`, `abstract`, `data-description`, `Prizes`. Principais achados novos:
- **μ0 = 600** (ver item 4).
- **Trilha Simulation em si não paga prêmio em dinheiro diretamente** — página "Prizes": "The Competition track itself does not include monetary prizes. However, participants who submit a report to the Hackathon track will be eligible for prize awards. Final rankings for Hackathon prizes will be determined based on both the Competition leaderboard performance and the Hackathon evaluation." Ou seja, o prêmio real (US$ 240.000, ver item 2) está atrelado à trilha Strategy/Hackathon, que avalia tanto o desempenho no leaderboard da Simulation quanto um relatório — reforça a importância de manter `docs/` completo para esse relatório (ver `CLAUDE.md`).
- Declaração do organizador (post de 16/06/2026, tópico 708586) sobre as diferenças conhecidas entre o simulador e as regras oficiais do TCG físico: 3 diferenças catalogadas (casos de ataque não-selecionável, ordem de dano do Mega Zygarde ex, ordem de captura de prêmios em knockout simultâneo), todas descritas pelo próprio organizador como de impacto mínimo/nulo na competição. Frase de fechamento: "In this competition, please note that the simulator behavior will be treated as the correct behavior."
- Declaração do organizador sobre a natureza do desafio: "Using rule-based programming alone may not ensure a high ranking... requires forward thinking, real-time adaptation, and optimal decision-making" — confirma que abordagens de heurística pura (como a nossa) têm um teto competitivo esperado, e que busca (MCTS via `search_begin`/`search_step`) ou RL são os caminhos para o topo do leaderboard.
- Banlist/regras de deck: nada além do já confirmado empiricamente (1x ACE SPEC).

## 7. Risco de cronograma

A trilha Simulation fecha em **16/08/2026** (confirmado, item 2) — a partir de hoje (07/08) restam ~9 dias. Com o contrato técnico já validado (item 1), o próximo risco é gastar tempo demais em pesquisa e pouco em ter uma submissão válida rodando cedo. Mitigação: seguir a ordem de fases do `02-estrategia-solucao.md` — baseline "nunca crasha" primeiro, otimização depois.
