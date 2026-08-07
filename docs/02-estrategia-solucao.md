# 02 · Estratégia de Solução

Plano faseado. Cada fase produz um artefato testável e submetível — evitamos ficar meses "pesquisando" sem nada rodando no ladder, porque **o ladder real é o único juiz confiável** (relatos de terceiros indicam que simulações locais nem sempre preveem o desempenho real no ladder).

## Fase 0 — Fundação ✅ concluída em 07/08/2026
- ~~Criar conta/aceitar regras nas duas competições.~~
- ~~Baixar starter kit, engine, exemplos oficiais.~~
- ~~Validar o contrato técnico descrito em `01-definicao-problema.md` contra a fonte oficial.~~ Feito via Kaggle API — `sample_submission/`, engine C++ (`ptcg_engine/`) e bases de carta baixados e lidos.
- **Falta ainda**: ler o texto de `/rules` (não é um arquivo de dados, é a página de regras em si — ver `06-riscos-questoes-abertas.md` item 6) e rodar o agente de exemplo ponta a ponta localmente (próximo passo real de código).

## Fase 1 — Baseline "burro, mas nunca crasha"
- Agente **rule-based** trivial: sempre escolhe a primeira ação legal / heurística mínima (ex.: sempre ataca se possível, senão avança o jogo).
- Deck inicial: copiar um arquétipo Standard conhecido e competitivamente razoável (evita gastar tempo em deckbuilding do zero antes de ter pipeline funcionando).
- Objetivo: ter uma submissão válida rodando no ladder o quanto antes, para começar a coletar sinal real (dado o prazo apertado da trilha Simulation).

## Fase 2 — Heurística de deckbuilding + agente com scoring
- Pesquisa de metagame Standard atual (quais arquétipos dominam, contadores conhecidos).
- Escolher/testar 2–3 arquétipos candidatos localmente via o engine `cabt` (matchup matrix entre eles).
- Agente evolui de "regra fixa" para **scoring de jogadas**: para cada ação legal, calcular uma heurística (dano esperado, cartas de prêmio, desenvolvimento de board) e escolher a melhor.

## Fase 3 — Busca / planejamento sob incerteza
- **Achado importante**: o engine oficial já expõe uma API de busca/lookahead (`search_begin`/`search_step`, ver `01-definicao-problema.md`) que permite simular partidas internamente, incluindo determinização de informação oculta (você informa uma hipótese de mão/deck do oponente e o engine simula a partir daí). Isso significa que MCTS **não exige reimplementar as regras do PTCG** — só a política de seleção de nós e a amostragem de hipóteses do oponente.
- Avaliar **MCTS** com determinização usando essa API, respeitando o limite de tempo por jogada (a confirmar, ver `06-riscos-questoes-abertas.md` item 5).
- Comparar contra a Fase 2 em avaliação local antes de gastar submissões.
- Critério de corte: só sobe pra produção se ganhar consistentemente da heurística pura em partidas locais controladas.

## Fase 4 (opcional/stretch) — Aprendizado por reforço
- Só se houver tempo sobrando após Fase 3 estar estável no ladder — **alto risco de custo/benefício** dado o prazo curto da trilha Simulation.
- Self-play com o `cabt` SDK local; usar o agente de busca (Fase 3) como oponente/baseline de avaliação.

## Fase 5 — Trilha Strategy (relatório)
- Consolidar: metodologia, decisões de deck, arquitetura do agente, resultados de matchup, o que funcionou vs não funcionou, gráficos de evolução de rating.
- Esta fase depende do agente da trilha Simulation já estar rodando e gerando dados — não pode começar do zero, é a "escrita" do que foi feito nas fases anteriores.

## Princípios que guiam as decisões técnicas

- **Nunca crashar > jogar bem.** Um crash é potencialmente uma partida perdida garantida.
- **Deck e agente são dois problemas separados** que se combinam — não confundir "meu agente é ruim" com "meu deck é ruim" (ver relato de terceiros: "deck choice > agent quality" para Elo alto).
- **Avaliação local antes de gastar submissões diárias** (limite reportado de 5/dia, 2 contam).
- **Simplicidade primeiro**: relatos de terceiros indicam que agentes baseados em regra pilotando decks simples superaram combos complexos no ladder real.
